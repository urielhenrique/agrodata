"""Integração espacial INMET → município IBGE (MVP2.2).

Fluxo:
    StationDimension (lat/lon EPSG:4326)
        → pontos EPSG:4326
        → to_crs(EPSG:4674)
        → spatial join (within) com Malha Municipal IBGE
        → station_id → municipio_id

Regras:
- Malha permanece em EPSG:4674 (fonte de verdade territorial).
- Pontos INMET nascem em EPSG:4326 e são reprojetados (nunca comparação mista).
- predicate="within" apenas. Sem nearest, sem buffer, sem tolerância.
- 1 município → matched | 0 → unmatched | >1 → ambiguous.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError
from shapely.geometry import Point

from agrodata.geospatial.integrate import _validar_malha_para_integracao
from agrodata.geospatial.load import (
    CAMINHO_MALHA_PROCESSADA,
    carregar_malha_geoparquet,
)
from agrodata.pipelines.inmet.schemas import StationDimension

logger = logging.getLogger(__name__)

CRS_ORIGEM = "EPSG:4326"
CRS_PROCESSAMENTO = "EPSG:4674"
VERSAO_MALHA = "IBGE_Malha_Municipal_2023_MG"

STATUS_MATCHED = "matched"
STATUS_UNMATCHED = "unmatched"
STATUS_AMBIGUOUS = "ambiguous"

METODO_WITHIN = "within"
METODO_SEM_ATRIBUICAO = "sem_atribuicao"

CAMINHO_STATION_MUNICIPALITY = Path(
    "data/processed/inmet/station_municipality/year=2023/uf=MG/part-0.parquet"
)

COLUNAS_LINK = [
    "station_id",
    "wmo_id",
    "municipio_id",
    "municipio_nome",
    "uf",
    "latitude",
    "longitude",
    "crs_origem",
    "crs_processamento",
    "metodo",
    "status",
    "versao_malha",
]

SCHEMA_LINK = pa.schema(
    [
        pa.field("station_id", pa.string()),
        pa.field("wmo_id", pa.string()),
        pa.field("municipio_id", pa.string()),
        pa.field("municipio_nome", pa.string()),
        pa.field("uf", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
        pa.field("crs_origem", pa.string()),
        pa.field("crs_processamento", pa.string()),
        pa.field("metodo", pa.string()),
        pa.field("status", pa.string()),
        pa.field("versao_malha", pa.string()),
    ]
)


@dataclass(frozen=True)
class RelatorioCobertura:
    """Cobertura do link estação → município."""

    total_estacoes: int
    matched: int
    unmatched: int
    ambiguous: int
    coordenadas_invalidas: int
    percentual_matched: float
    erros: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_estacoes": self.total_estacoes,
            "matched": self.matched,
            "unmatched": self.unmatched,
            "ambiguous": self.ambiguous,
            "coordenadas_invalidas": self.coordenadas_invalidas,
            "percentual_matched": self.percentual_matched,
            "erros": self.erros,
        }


def _coordenada_valida(latitude: float | None, longitude: float | None) -> bool:
    """Reaproveita os limites do StationDimension (graus decimais)."""
    if latitude is None or longitude is None:
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _validar_municipio_id(valor: str | None) -> str | None:
    """Garante string de 7 dígitos vinda da malha; None permanece None."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    texto = str(valor)
    if texto in ("", "None", "nan", "<NA>"):
        return None
    if len(texto) != 7:
        raise RuntimeError(f"municipio_id com tamanho != 7 vindo da malha: {valor!r}")
    return texto


def estacoes_para_pontos(stations: list[StationDimension]) -> gpd.GeoDataFrame:
    """Transforma StationDimension em pontos EPSG:4326.

    Estações com coordenada inválida são excluídas aqui e contabilizadas
    separadamente via :func:`contar_coordenadas_invalidas`.
    """
    linhas = []
    for s in stations:
        if not _coordenada_valida(s.latitude, s.longitude):
            continue
        linhas.append(
            {
                "station_id": s.station_id,
                "wmo_id": s.wmo_id,
                "uf": s.uf,
                "latitude": float(s.latitude),
                "longitude": float(s.longitude),
                "geometry": Point(float(s.longitude), float(s.latitude)),
            }
        )
    if not linhas:
        return gpd.GeoDataFrame(
            {
                "station_id": pd.Series(dtype="string"),
                "wmo_id": pd.Series(dtype="string"),
                "uf": pd.Series(dtype="string"),
                "latitude": pd.Series(dtype="float64"),
                "longitude": pd.Series(dtype="float64"),
                "geometry": gpd.GeoSeries([], crs=CRS_ORIGEM),
            },
            geometry="geometry",
            crs=CRS_ORIGEM,
        )
    gdf = gpd.GeoDataFrame(linhas, geometry="geometry", crs=CRS_ORIGEM)
    return gdf


def contar_coordenadas_invalidas(stations: list[StationDimension]) -> int:
    """Conta estações com latitude/longitude inválidas (fora do join)."""
    return sum(1 for s in stations if not _coordenada_valida(s.latitude, s.longitude))


def reprojetar_para_processamento(gdf_pontos: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reprojeta pontos de EPSG:4326 para EPSG:4674."""
    if gdf_pontos.crs is None or gdf_pontos.crs.to_epsg() != 4326:
        raise ValueError(f"Pontos devem estar em EPSG:4326, recebido: {gdf_pontos.crs}")
    return gdf_pontos.to_crs(CRS_PROCESSAMENTO)


def _validar_malha_para_link(gdf_malha: gpd.GeoDataFrame) -> None:
    """Valida malha para o link (reutiliza validadores do MVP1)."""
    erros = _validar_malha_para_integracao(gdf_malha)
    if gdf_malha.crs is None or gdf_malha.crs.to_epsg() != 4674:
        erros.append(f"Malha deve estar em EPSG:4674, recebido: {gdf_malha.crs}")
    if erros:
        raise RuntimeError("Validacao da malha para link falhou:\n" + "\n".join(erros))


def atribuir_municipios(
    pontos_4674: gpd.GeoDataFrame,
    gdf_malha: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Atribui município via point-in-polygon (predicate within).

    Retorna DataFrame com o schema do link (sem coordenadas inválidas;
    essas entram apenas no relatório).
    """
    if pontos_4674.crs is None or pontos_4674.crs.to_epsg() != 4674:
        raise ValueError("Pontos devem estar em EPSG:4674 para o join.")
    _validar_malha_para_link(gdf_malha)

    if len(pontos_4674) == 0:
        return pd.DataFrame(columns=COLUNAS_LINK)

    malha_join = gpd.GeoDataFrame(
        gdf_malha[["municipio_id", "municipio_nome", "geometry"]].copy(),
        geometry="geometry",
        crs=gdf_malha.crs,
    )
    joined = gpd.sjoin(pontos_4674, malha_join, how="left", predicate="within")

    linhas: list[dict] = []
    for station_id, grupo in joined.groupby("station_id", sort=False):
        primeira = grupo.iloc[0]
        candidatos = grupo["municipio_id"].dropna().astype(str).unique().tolist()
        if len(candidatos) == 1:
            status = STATUS_MATCHED
            metodo = METODO_WITHIN
            municipio_id = _validar_municipio_id(candidatos[0])
            nomes = grupo.loc[
                grupo["municipio_id"].astype(str) == candidatos[0], "municipio_nome"
            ]
            municipio_nome = str(nomes.iloc[0]) if len(nomes) else None
        elif len(candidatos) == 0:
            status = STATUS_UNMATCHED
            metodo = METODO_SEM_ATRIBUICAO
            municipio_id = None
            municipio_nome = None
        else:
            status = STATUS_AMBIGUOUS
            metodo = METODO_SEM_ATRIBUICAO
            municipio_id = None
            municipio_nome = None
        linhas.append(
            {
                "station_id": str(station_id),
                "wmo_id": None if pd.isna(primeira["wmo_id"]) else str(primeira["wmo_id"]),
                "municipio_id": municipio_id,
                "municipio_nome": municipio_nome,
                "uf": str(primeira["uf"]),
                "latitude": float(primeira["latitude"]),
                "longitude": float(primeira["longitude"]),
                "crs_origem": CRS_ORIGEM,
                "crs_processamento": CRS_PROCESSAMENTO,
                "metodo": metodo,
                "status": status,
                "versao_malha": VERSAO_MALHA,
            }
        )
    df = pd.DataFrame(linhas, columns=COLUNAS_LINK)
    for coluna in ["station_id", "wmo_id", "municipio_id", "municipio_nome", "uf"]:
        df[coluna] = df[coluna].astype("string")
    return df


def gerar_relatorio_cobertura(
    df_link: pd.DataFrame,
    coordenadas_invalidas: int,
) -> RelatorioCobertura:
    """Gera relatório tipado de cobertura."""
    matched = int((df_link["status"] == STATUS_MATCHED).sum()) if len(df_link) else 0
    unmatched = int((df_link["status"] == STATUS_UNMATCHED).sum()) if len(df_link) else 0
    ambiguous = int((df_link["status"] == STATUS_AMBIGUOUS).sum()) if len(df_link) else 0
    total = matched + unmatched + ambiguous + coordenadas_invalidas
    percentual = round(matched / total * 100, 2) if total else 0.0
    return RelatorioCobertura(
        total_estacoes=total,
        matched=matched,
        unmatched=unmatched,
        ambiguous=ambiguous,
        coordenadas_invalidas=coordenadas_invalidas,
        percentual_matched=percentual,
    )


def vincular_estacoes_municipios(
    stations: list[StationDimension],
    gdf_malha: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, RelatorioCobertura]:
    """Pipeline em memória: pontos → reprojeção → join → relatório."""
    coordenadas_invalidas = contar_coordenadas_invalidas(stations)
    pontos_4326 = estacoes_para_pontos(stations)
    pontos_4674 = (
        reprojetar_para_processamento(pontos_4326)
        if len(pontos_4326)
        else pontos_4326.set_crs(CRS_PROCESSAMENTO, allow_override=True)
    )
    df_link = atribuir_municipios(pontos_4674, gdf_malha)
    relatorio = gerar_relatorio_cobertura(df_link, coordenadas_invalidas)
    return df_link, relatorio


def salvar_station_municipality(df: pd.DataFrame, caminho: Path | str) -> Path:
    """Salva a tabela de relacionamento em Parquet (PyArrow, snappy)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df_ordem = df.reindex(columns=COLUNAS_LINK)
    table = pa.Table.from_pandas(df_ordem, schema=SCHEMA_LINK, preserve_index=False)
    pq.write_table(table, caminho, compression="snappy", use_dictionary=True)
    logger.info("station_municipality salvo: %s (%d linhas)", caminho, len(df_ordem))
    return caminho.resolve()


def carregar_station_municipality(caminho: Path | str) -> pd.DataFrame:
    """Carrega a tabela de relacionamento."""
    return pd.read_parquet(Path(caminho), engine="pyarrow")


def _linhas_para_stations(
    df: pd.DataFrame, extracted_at_default: str = "", run_id_default: str = "link"
) -> tuple[list[StationDimension], int]:
    """Converte linhas de stations.parquet em StationDimension.

    Retorna (stations válidas, n_coordenadas_invalidas). Linhas que falham na
    validação Pydantic contam como coordenadas inválidas, sem apagar a origem.
    """
    stations: list[StationDimension] = []
    invalidas = 0
    for _, row in df.iterrows():
        try:
            stations.append(
                StationDimension(
                    station_id=str(row["station_id"]),
                    wmo_id=None if pd.isna(row.get("wmo_id")) else str(row["wmo_id"]),
                    name=str(row.get("name", row["station_id"])),
                    uf=str(row.get("uf", "MG")),
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    altitude=None
                    if pd.isna(row.get("altitude"))
                    else float(row["altitude"]),
                    extracted_at=pd.to_datetime(
                        row.get("extracted_at", "2023-01-01"), utc=True
                    ).to_pydatetime(),
                    ingestion_run_id=str(row.get("ingestion_run_id", run_id_default)),
                )
            )
        except (ValidationError, TypeError, ValueError):
            invalidas += 1
    return stations, invalidas


def executar_link_estacoes(
    caminho_stations: Path | str,
    caminho_malha: Path | str | None = None,
    caminho_saida: Path | str | None = None,
    ano: int = 2023,
    uf: str = "MG",
) -> tuple[pd.DataFrame, RelatorioCobertura]:
    """Orquestra o link espacial stations.parquet → station_municipality.

    Não mistura ingestão meteorológica com integração espacial; apenas lê os
    artefatos já persistidos. Paths injetáveis para testes.

    Args:
        caminho_stations: stations.parquet (ou diretório contendo).
        caminho_malha: GeoParquet da malha. Padrão: CAMINHO_MALHA_PROCESSADA.
        caminho_saida: saída part-0.parquet. Padrão derivado de ano/uf.
        ano: ano do particionamento de saída.
        uf: UF do particionamento de saída.
    """
    caminho_stations = Path(caminho_stations)
    if caminho_malha is None:
        caminho_malha = CAMINHO_MALHA_PROCESSADA
    if caminho_saida is None:
        caminho_saida = (
            Path("data/processed/inmet/station_municipality")
            / f"year={ano}"
            / f"uf={uf}"
            / "part-0.parquet"
        )
    df_stations = pd.read_parquet(caminho_stations, engine="pyarrow")
    stations, invalidas_parse = _linhas_para_stations(df_stations)
    gdf_malha = carregar_malha_geoparquet(caminho_malha)
    df_link, relatorio = vincular_estacoes_municipios(stations, gdf_malha)
    # Soma falhas de parse (ex.: lat/lon ausentes no parquet) às inválidas.
    if invalidas_parse:
        relatorio = RelatorioCobertura(
            total_estacoes=relatorio.total_estacoes + invalidas_parse,
            matched=relatorio.matched,
            unmatched=relatorio.unmatched,
            ambiguous=relatorio.ambiguous,
            coordenadas_invalidas=relatorio.coordenadas_invalidas + invalidas_parse,
            percentual_matched=round(
                relatorio.matched
                / (relatorio.total_estacoes + invalidas_parse)
                * 100,
                2,
            )
            if (relatorio.total_estacoes + invalidas_parse)
            else 0.0,
        )
    salvar_station_municipality(df_link, caminho_saida)
    return df_link, relatorio
