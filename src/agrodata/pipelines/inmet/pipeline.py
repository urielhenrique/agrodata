"""Orquestração do pipeline INMET/BDMEP."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agrodata.pipelines.inmet.client import INMETClient
from agrodata.pipelines.inmet.load import (
    salvar_observations,
    salvar_stations,
)
from agrodata.pipelines.inmet.parser import (
    extrair_zip,
    parser_csv_para_registros,
)
from agrodata.pipelines.inmet.quality import QualityReport, verificar_qualidade
from agrodata.pipelines.inmet.station_catalog import (
    construir_station_dimension,
    extrair_metadados_todas_estacoes,
    filtrar_estacoes_uf,
)
from agrodata.pipelines.inmet.transform import (
    gerar_ingestion_run_id,
    transformar_registros,
)

logger = __import__("logging").getLogger(__name__)


@dataclass(frozen=True)
class ConfigPipelineINMET:
    """Configuração explícita e tipada para o pipeline INMET/BDMEP."""

    ano: int = 2023
    uf: str = "MG"
    raiz_raw: Path = field(default_factory=lambda: Path("data/raw"))
    raiz_processed: Path = field(default_factory=lambda: Path("data/processed"))
    max_estacoes: int | None = None
    reutilizar_raw: bool = True
    permitir_sobrescrever_raw: bool = False

    def __post_init__(self) -> None:
        if not (2000 <= self.ano <= 2030):
            raise ValueError(f"Ano fora do intervalo suportado: {self.ano}")


@dataclass(frozen=True)
class MetricasPipelineINMET:
    """Métricas de execução do pipeline INMET."""

    config: ConfigPipelineINMET
    ingestion_run_id: str
    ano: int
    uf: str
    estações_processadas: int
    estações_com_dados: int
    registros_lidos: int
    registros_normalizados: int
    registros_missing: int
    registros_suspect: int
    registros_out_of_range: int
    duplicidades: int
    gaps_temporais_24h: int
    estacoes_sem_metadata: int
    erros: int
    warnings: int
    qualidade_valida: bool
    tempo_total_seg: float
    tempo_download_seg: float
    tempo_parser_seg: float
    tempo_transform_seg: float
    tempo_quality_seg: float
    tempo_load_seg: float
    caminho_raw: str
    caminho_observations: str
    caminho_stations: str


def _caminho_raw_zip(config: ConfigPipelineINMET, raiz: Path) -> Path:
    return raiz / config.raiz_raw / "inmet" / str(config.ano) / f"BDMEP_{config.ano}.zip"


def _caminho_extraido(config: ConfigPipelineINMET, raiz: Path) -> Path:
    return raiz / config.raiz_raw / "inmet" / str(config.ano) / "extracted"


def executar_pipeline(
    config: ConfigPipelineINMET | None = None,
    *,
    raiz: Path | None = None,
) -> MetricasPipelineINMET:
    """Executa o pipeline completo INMET/BDMEP.

    Fluxo:
        1. Download do ZIP anual (ou reutilização de RAW existente)
        2. Extração dos CSVs
        3. Catálogo de estações (metadata + filtro UF)
        4. Parsing CSVs → registros brutos
        5. Transformação → ObservacaoHoraria + StationDimension
        6. Qualidade → QualityReport
        7. Persistência Parquet (observations_hourly + stations)
        8. Retorno de métricas

    Args:
        config: Configuração do pipeline. Usa padrões se None.
        raiz: Diretório raiz do projeto. Auto-detecta se None.

    Returns:
        Métricas de execução do pipeline.
    """
    if config is None:
        config = ConfigPipelineINMET()

    if raiz is None:
        raiz = Path(__file__).resolve().parents[3]

    ingestion_run_id = gerar_ingestion_run_id()
    extracted_at = datetime.now(UTC)

    logger.info("Iniciando pipeline INMET/BDMEP")
    logger.info("Config: ano=%d, uf=%s, max_estacoes=%s", config.ano, config.uf, config.max_estacoes)

    tempo_inicio = time.perf_counter()
    tempo_download = 0.0
    tempo_parser = 0.0
    tempo_transform = 0.0
    tempo_quality = 0.0
    tempo_load = 0.0

    caminho_raw = _caminho_raw_zip(config, raiz)
    caminho_extraido = _caminho_extraido(config, raiz)

    # --- Etapa 1: Download (ou reutilização) ---
    tempo_download_inicio = time.perf_counter()

    if caminho_raw.exists() and config.reutilizar_raw:
        logger.info("RAW existente encontrado: %s — reutilizando", caminho_raw)
    else:
        if caminho_raw.exists() and not config.permitir_sobrescrever_raw:
            raise FileExistsError(
                f"RAW já existe: {caminho_raw}. "
                "Use permitir_sobrescrever_raw=True ou reutilizar_raw=True."
            )

        with INMETClient() as client:
            client.download_anual(config.ano, caminho_raw.parent)

    tempo_download = time.perf_counter() - tempo_download_inicio

    # --- Etapa 2: Extração ---
    logger.info("Extraindo CSVs do ZIP...")
    csvs = extrair_zip(caminho_raw, caminho_extraido)

    if config.max_estacoes:
        csvs = csvs[:config.max_estacoes]

    logger.info("CSVs extraídos: %d estações", len(csvs))

    # --- Etapa 3: Catálogo de estações (metadata) ---
    logger.info("Extraindo metadados das estações...")
    metadados_todas = extrair_metadados_todas_estacoes(caminho_raw, caminho_extraido)
    metadados_uf = filtrar_estacoes_uf(metadados_todas, config.uf)
    estacoes_conhecidas = set(metadados_uf.keys())
    stations = construir_station_dimension(metadados_uf, extracted_at, ingestion_run_id)
    logger.info("Estações com metadata válida (%s): %d", config.uf, len(stations))

    # --- Etapa 4: Parsing CSVs ---
    tempo_parser_inicio = time.perf_counter()

    registros_brutos = []
    for csv_path in csvs:
        station_id = csv_path.stem
        if station_id not in estacoes_conhecidas:
            continue
        registros_brutos.extend(
            parser_csv_para_registros(csv_path, extracted_at.isoformat(), ingestion_run_id)
        )

    logger.info("Registros brutos lidos: %d", len(registros_brutos))

    tempo_parser = time.perf_counter() - tempo_parser_inicio

    # --- Etapa 5: Transformação ---
    tempo_transform_inicio = time.perf_counter()

    observacoes, _ = transformar_registros(
        iter(registros_brutos), extracted_at, ingestion_run_id
    )

    logger.info("Registros normalizados: %d", len(observacoes))

    tempo_transform = time.perf_counter() - tempo_transform_inicio

    # --- Etapa 6: Qualidade ---
    tempo_quality_inicio = time.perf_counter()

    quality_report: QualityReport = verificar_qualidade(observacoes, estacoes_conhecidas)

    logger.info("Quality Report: %s", quality_report.to_dict())

    if not quality_report.valido:
        raise RuntimeError(
            f"Falha de qualidade - qualidade inválida: "
            f"erros={quality_report.erros}, "
            f"warnings={quality_report.warnings}, "
            f"duplicidades_pk={quality_report.duplicidades_pk}, "
            f"temperatura_fora_faixa={quality_report.contagem_por_regra.get('temperatura_fora_faixa', 0)}"
        )

    tempo_quality = time.perf_counter() - tempo_quality_inicio

    # --- Etapa 7: Persistência ---
    tempo_load_inicio = time.perf_counter()

    caminho_obs = salvar_observations(observacoes, raiz / config.raiz_processed, config.ano, config.uf)
    caminho_st = salvar_stations(stations, raiz / config.raiz_processed)

    logger.info("Observations salvo: %s", caminho_obs)
    logger.info("Stations salvo: %s", caminho_st)

    tempo_load = time.perf_counter() - tempo_load_inicio

    tempo_total = time.perf_counter() - tempo_inicio

    contagem_flag = quality_report.contagem_por_flag

    return MetricasPipelineINMET(
        config=config,
        ingestion_run_id=ingestion_run_id,
        ano=config.ano,
        uf=config.uf,
        estações_processadas=len(csvs),
        estações_com_dados=len(estacoes_conhecidas),
        registros_lidos=len(registros_brutos),
        registros_normalizados=len(observacoes),
        registros_missing=contagem_flag.get("missing", 0),
        registros_suspect=contagem_flag.get("suspect", 0),
        registros_out_of_range=contagem_flag.get("out_of_range", 0),
        duplicidades=quality_report.duplicidades_pk,
        gaps_temporais_24h=quality_report.gaps_temporais_maiores_24h,
        estacoes_sem_metadata=quality_report.estacoes_sem_metadata,
        erros=quality_report.erros,
        warnings=quality_report.warnings,
        qualidade_valida=quality_report.valido,
        tempo_total_seg=round(tempo_total, 3),
        tempo_download_seg=round(tempo_download, 3),
        tempo_parser_seg=round(tempo_parser, 3),
        tempo_transform_seg=round(tempo_transform, 3),
        tempo_quality_seg=round(tempo_quality, 3),
        tempo_load_seg=round(tempo_load, 3),
        caminho_raw=str(caminho_raw.resolve()),
        caminho_observations=str(caminho_obs.resolve()) if caminho_obs else "",
        caminho_stations=str(caminho_st.resolve()) if caminho_st else "",
    )