"""Integração da Malha Municipal IBGE com o dataset analítico PAM."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd

from agrodata.geospatial.load import (
    CAMINHO_MALHA_PROCESSADA,
    carregar_malha_geoparquet,
)

logger = logging.getLogger(__name__)

CAMINHO_PAM_ANALYTICS = Path(
    "data/processed/ibge/pam/pam_5457_2023_mg_soja_milho_analytics.parquet"
)

CAMINHO_INTEGRADO = Path(
    "data/processed/ibge/malha_municipal/mg_pam_2023_soja_milho.parquet"
)

CHAVE_AGRICOLA = ["municipio_id", "produto_codigo", "periodo"]


@dataclass(frozen=True)
class ResultadoIntegracao:
    """Resultado da integração PAM × Malha."""

    linhas_pam: int
    linhas_resultado: int
    municipios_pam: int
    municipios_malha: int
    municipios_pam_com_geometry: int
    municipios_malha_sem_pam: int
    chaves_duplicadas: int
    crs: str
    valido: bool
    erros: list[str] = field(default_factory=list)


def _validar_malha_para_integracao(gdf_malha: gpd.GeoDataFrame) -> list[str]:
    """Valida a malha municipal antes da integração."""
    erros = []

    if not isinstance(gdf_malha, gpd.GeoDataFrame):
        erros.append("Objeto nao e um GeoDataFrame")
        return erros

    if "municipio_id" not in gdf_malha.columns:
        erros.append("municipio_id ausente na malha")
    else:
        if gdf_malha["municipio_id"].isna().any():
            erros.append("municipio_id possui nulos na malha")
        if gdf_malha["municipio_id"].duplicated().any():
            erros.append("municipio_id duplicado na malha")
        if (gdf_malha["municipio_id"].astype(str).str.len() != 7).any():
            erros.append("municipio_id com tamanho != 7 na malha")

    if "geometry" not in gdf_malha.columns:
        erros.append("geometry ausente na malha")
    elif gdf_malha.geometry.isna().any():
        erros.append("geometry possui nulos na malha")
    elif (~gdf_malha.geometry.is_valid).any():
        erros.append("geometry possui geometrias invalidas na malha")

    if gdf_malha.crs is None:
        erros.append("CRS nao definido na malha")

    return erros


def _validar_pam_para_integracao(pam: pd.DataFrame) -> list[str]:
    """Valida o PAM analítico antes da integração."""
    erros = []

    if "municipio_id" not in pam.columns:
        erros.append("municipio_id ausente no PAM")
    else:
        if pam["municipio_id"].isna().any():
            erros.append("municipio_id possui nulos no PAM")
        if (pam["municipio_id"].astype(str).str.len() != 7).any():
            erros.append("municipio_id com tamanho != 7 no PAM")

    colunas_chave_faltantes = [c for c in CHAVE_AGRICOLA if c not in pam.columns]
    if colunas_chave_faltantes:
        erros.append(f"Colunas da chave agricola ausentes no PAM: {colunas_chave_faltantes}")
    else:
        duplicatas = pam.duplicated(subset=CHAVE_AGRICOLA).sum()
        if duplicatas > 0:
            erros.append(f"Chave agricola duplicada no PAM: {duplicatas}")

    return erros


def integrar_pam_com_malha(
    pam: pd.DataFrame,
    gdf_malha: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, ResultadoIntegracao]:
    """Integra o dataset analítico PAM com a malha municipal.

    Operação: PAM LEFT JOIN MALHA pela chave municipio_id.

    Preserva todas as observações agrícolas do PAM e adiciona
    geometria e atributos territoriais da malha.

    Args:
        pam: DataFrame analítico PAM (já carregado).
        gdf_malha: GeoDataFrame da malha municipal normalizada.

    Returns:
        Tupla (GeoDataFrame integrado, ResultadoIntegracao).

    Raises:
        RuntimeError: Se validações de integridade falharem.
    """
    logger.info("Iniciando integracao PAM x Malha")
    logger.info("PAM: %d linhas, Malha: %d municipios", len(pam), len(gdf_malha))

    # Validações prévias
    erros_malha = _validar_malha_para_integracao(gdf_malha)
    erros_pam = _validar_pam_para_integracao(pam)

    if erros_malha or erros_pam:
        todos_erros = erros_malha + erros_pam
        logger.error("Validacao pre-integracao falhou: %s", todos_erros)
        raise RuntimeError(
            "Validacao pre-integracao falhou:\n" + "\n".join(todos_erros)
        )

    # Verificar cobertura: todos os municipios do PAM existem na malha?
    municipios_pam = set(pam["municipio_id"].unique())
    municipios_malha = set(gdf_malha["municipio_id"].unique())

    pam_sem_geometry = municipios_pam - municipios_malha
    if pam_sem_geometry:
        raise RuntimeError(
            f"Municipios do PAM nao encontrados na malha: {sorted(pam_sem_geometry)}"
        )

    # Colunas da malha para trazer (excluir municipio_id que é a chave)
    # Remover municipio_nome do PAM para evitar conflito - a malha é a autoridade
    colunas_malha = [
        "municipio_nome",
        "uf",
        "area_km2",
        "geometry",
    ]
    # Incluir cd_uf se existir
    if "cd_uf" in gdf_malha.columns:
        colunas_malha.insert(1, "cd_uf")

    # PAM: remover municipio_nome se existir (evita conflito _x/_y)
    # Remover nivel_territorial_* que nao fazem parte do resultado final
    pam_join = pam.drop(
        columns=["municipio_nome", "nivel_territorial_id", "nivel_territorial_nome"],
        errors="ignore",
    )

    # PAM LEFT JOIN Malha
    gdf_malha_join = gdf_malha[["municipio_id"] + colunas_malha].copy()

    gdf_integrado = pam_join.merge(
        gdf_malha_join,
        on="municipio_id",
        how="left",
        validate="many_to_one",
    )

    # Converter para GeoDataFrame
    gdf_integrado = gpd.GeoDataFrame(gdf_integrado, geometry="geometry", crs=gdf_malha.crs)

    logger.info(
        "Join concluido: %d linhas PAM -> %d linhas integradas",
        len(pam),
        len(gdf_integrado),
    )

    # Validações pós-join
    linhas_pam = len(pam)
    linhas_resultado = len(gdf_integrado)
    municipios_pam_count = pam["municipio_id"].nunique()
    municipios_malha_count = len(municipios_malha)
    municipios_pam_com_geometry = gdf_integrado["municipio_id"].nunique()
    municipios_malha_sem_pam = len(municipios_malha - municipios_pam)
    chaves_duplicadas = gdf_integrado.duplicated(subset=CHAVE_AGRICOLA).sum()
    crs = str(gdf_integrado.crs) if gdf_integrado.crs else None

    erros_pos = []
    if linhas_resultado != linhas_pam:
        erros_pos.append(
            f"Cardinalidade alterada: {linhas_pam} -> {linhas_resultado}"
        )
    if gdf_integrado.geometry.isna().any():
        erros_pos.append("Geometry possui nulos apos join")
    if (~gdf_integrado.geometry.is_valid).any():
        erros_pos.append("Geometry invalida apos join")
    if chaves_duplicadas > 0:
        erros_pos.append(f"Chave agricola duplicada no resultado: {chaves_duplicadas}")

    valido = len(erros_pos) == 0

    resultado = ResultadoIntegracao(
        linhas_pam=linhas_pam,
        linhas_resultado=linhas_resultado,
        municipios_pam=municipios_pam_count,
        municipios_malha=municipios_malha_count,
        municipios_pam_com_geometry=municipios_pam_com_geometry,
        municipios_malha_sem_pam=municipios_malha_sem_pam,
        chaves_duplicadas=int(chaves_duplicadas),
        crs=crs,
        valido=valido,
        erros=erros_pos,
    )

    if not valido:
        logger.error("Validacao pos-integracao falhou: %s", erros_pos)
        raise RuntimeError(
            "Validacao pos-integracao falhou:\n" + "\n".join(erros_pos)
        )

    logger.info(
        "Integracao validada: %d linhas, %d municipios PAM, %d municipios malha sem PAM",
        resultado.linhas_resultado,
        resultado.municipios_pam,
        resultado.municipios_malha_sem_pam,
    )

    return gdf_integrado, resultado


def executar_integracao(
    caminho_pam: Path | None = None,
    caminho_malha: Path | None = None,
    caminho_saida: Path | None = None,
) -> gpd.GeoDataFrame:
    """Executa a integração completa PAM × Malha.

    Carrega ambos os arquivos, integra, valida e salva o resultado.

    Args:
        caminho_pam: Caminho do PAM analítico. Padrão: caminho do projeto.
        caminho_malha: Caminho da malha municipal. Padrão: caminho do projeto.
        caminho_saida: Caminho de saída do GeoParquet integrado. Padrão: caminho do projeto.

    Returns:
        GeoDataFrame integrado.
    """
    if caminho_pam is None:
        caminho_pam = CAMINHO_PAM_ANALYTICS
    if caminho_malha is None:
        caminho_malha = CAMINHO_MALHA_PROCESSADA
    if caminho_saida is None:
        caminho_saida = CAMINHO_INTEGRADO

    logger.info("Carregando PAM analitico de: %s", caminho_pam)
    pam = pd.read_parquet(caminho_pam)

    logger.info("Carregando malha municipal de: %s", caminho_malha)
    gdf_malha = carregar_malha_geoparquet(caminho_malha)

    gdf_integrado, _ = integrar_pam_com_malha(pam, gdf_malha)

    # Salvar resultado
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    gdf_integrado.to_parquet(caminho_saida, engine="pyarrow", index=False)
    logger.info("GeoParquet integrado salvo em: %s", caminho_saida)

    return gdf_integrado