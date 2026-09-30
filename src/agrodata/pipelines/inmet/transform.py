"""Transformação de dados brutos INMET para modelos normalizados."""

from __future__ import annotations

import logging
from collections.abc import Generator
from datetime import datetime
from uuid import uuid4

from pydantic import ValidationError

from agrodata.pipelines.inmet.schemas import ObservacaoHoraria, StationDimension

logger = logging.getLogger(__name__)


def _normalizar_valor_missing(valor: float | None, quality_flag: str) -> tuple[float | None, str]:
    """Normaliza valores missing."""
    if valor is None:
        return None, "missing"
    return valor, quality_flag


def _validar_faixa_temperatura(valor: float | None) -> str:
    """Valida se temperatura está em faixa física plausível."""
    if valor is None:
        return "valid"
    if valor < -50 or valor > 60:
        return "out_of_range"
    return "valid"


def _validar_faixa_precipitacao(valor: float | None) -> str:
    """Valida se precipitação está em faixa plausível."""
    if valor is None:
        return "valid"
    if valor < 0:
        return "out_of_range"
    if valor > 500:
        return "suspect"
    return "valid"


def transformar_registros(
    registros_brutos: Generator[dict],
    extracted_at: datetime,
    ingestion_run_id: str,
) -> tuple[list[ObservacaoHoraria], dict[str, dict]]:
    """Transforma registros brutos do parser em ObservacaoHoraria válidos.

    Args:
        registros_brutos: Gerador de dicionários do parser.
        extracted_at: Timestamp da extração.
        ingestion_run_id: UUID da execução.

    Returns:
        Tupla (lista de ObservacaoHoraria, dict de metadados de estações por station_id).
    """
    observacoes: list[ObservacaoHoraria] = []
    estacoes_meta: dict[str, dict] = {}

    for reg in registros_brutos:
        station_meta = reg.pop("_station_meta", {})
        if reg["station_id"] not in estacoes_meta:
            estacoes_meta[reg["station_id"]] = station_meta

        variable = reg["variable"]
        value = reg["value"]
        quality_flag = reg["quality_flag"]

        if value is not None:
            if variable == "precipitacao":
                quality_flag = _validar_faixa_precipitacao(value)
            elif variable in ("temp_max", "temp_min"):
                quality_flag = _validar_faixa_temperatura(value)

        value, quality_flag = _normalizar_valor_missing(value, quality_flag)

        reg["extracted_at"] = extracted_at
        reg["ingestion_run_id"] = ingestion_run_id
        reg["quality_flag"] = quality_flag

        try:
            obs = ObservacaoHoraria(**reg)
            observacoes.append(obs)
        except (ValidationError, TypeError, ValueError) as e:
            logger.debug("Erro ao criar ObservacaoHoraria: %s", e)

    return observacoes, estacoes_meta


def construir_dim_station(
    estacoes_meta: dict[str, dict],
    extracted_at: datetime,
    ingestion_run_id: str,
) -> list[StationDimension]:
    """Constrói dimensão StationDimension a partir dos metadados extraídos."""
    stations: list[StationDimension] = []

    for station_id, meta in estacoes_meta.items():
        try:
            lat = _parsear_coordenada(meta.get("latitude", ""))
            lon = _parsear_coordenada(meta.get("longitude", ""))
            alt = _parsear_altitude(meta.get("altitude", ""))

            if lat is None or lon is None:
                continue

            station = StationDimension(
                station_id=station_id,
                wmo_id=meta.get("wmo_id") or None,
                name=meta.get("station_name", station_id),
                uf=meta.get("uf", "MG"),
                latitude=lat,
                longitude=lon,
                altitude=alt,
                data_inicio=None,
                data_fim=None,
                extracted_at=extracted_at,
                ingestion_run_id=ingestion_run_id,
            )
            stations.append(station)
        except (ValidationError, TypeError, ValueError) as e:
            logger.debug("Erro ao criar StationDimension: %s", e)
            continue

    return stations


def _parsear_coordenada(valor: str) -> float | None:
    if not valor or valor.strip() == "":
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def _parsear_altitude(valor: str) -> float | None:
    if not valor or valor.strip() == "":
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def gerar_ingestion_run_id() -> str:
    """Gera UUID único para a execução do pipeline."""
    return str(uuid4())