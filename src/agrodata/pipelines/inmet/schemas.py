"""Schemas Pydantic para dados climáticos INMET/BDMEP."""

from __future__ import annotations

from datetime import datetime as dt_datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

VARIAVEIS_PERMITIDAS = frozenset({"precipitacao", "temp_max", "temp_min"})


class ObservacaoHoraria(BaseModel):
    """Registro horário normalizado de observação climática."""

    station_id: str = Field(..., description="Código INMET da estação (ex: A808)")
    datetime: dt_datetime = Field(..., description="Timestamp UTC da observação (horária)")
    variable: Literal["precipitacao", "temp_max", "temp_min"] = Field(...)
    value: float | None = Field(default=None, description="Valor numérico; None se missing")
    source: Literal["INMET_BDMEP"] = "INMET_BDMEP"
    extracted_at: dt_datetime = Field(..., description="Quando o ZIP foi baixado/processado")
    raw_row_hash: str = Field(..., description="SHA256 da linha bruta do CSV (dedup)")
    ingestion_run_id: str = Field(..., description="UUID da execução do pipeline")
    quality_flag: Literal["valid", "missing", "out_of_range", "suspect"] = "valid"

    @field_validator("variable")
    @classmethod
    def _validar_variavel(cls, v: str) -> str:
        if v not in VARIAVEIS_PERMITIDAS:
            raise ValueError(f"Variável inválida: {v}. Permitidas: {VARIAVEIS_PERMITIDAS}")
        return v

    @field_validator("value", mode="before")
    @classmethod
    def _parse_missing(cls, v):
        if v in (-9999, "-9999", "", None):
            return None
        return v


class StationDimension(BaseModel):
    """Dimensão de estação meteorológica."""

    station_id: str = Field(..., description="Código INMET (ex: A808)")
    wmo_id: str | None = Field(default=None, description="Código WMO se disponível")
    name: str = Field(..., description="Nome da estação (ex: BELO HORIZONTE)")
    uf: str = Field(..., description="UF (ex: MG)")
    latitude: float = Field(..., ge=-90, le=90, description="Graus decimais WGS84")
    longitude: float = Field(..., ge=-180, le=180, description="Graus decimais WGS84")
    altitude: float | None = Field(default=None, description="Metros acima do nível do mar")
    data_inicio: dt_datetime | None = Field(default=None, description="Primeiro registro disponível")
    data_fim: dt_datetime | None = Field(default=None, description="Último registro disponível")
    source: Literal["INMET_BDMEP"] = "INMET_BDMEP"
    extracted_at: dt_datetime = Field(...)
    ingestion_run_id: str = Field(...)


COLUNAS_OBSERVACAO: dict[str, str] = {
    "station_id": "string",
    "datetime": "timestamp[us, tz=UTC]",
    "variable": "string",
    "value": "float64",
    "source": "string",
    "extracted_at": "timestamp[us, tz=UTC]",
    "raw_row_hash": "string",
    "ingestion_run_id": "string",
    "quality_flag": "string",
}

COLUNAS_STATION: dict[str, str] = {
    "station_id": "string",
    "wmo_id": "string",
    "name": "string",
    "uf": "string",
    "latitude": "float64",
    "longitude": "float64",
    "altitude": "float64",
    "data_inicio": "timestamp[us, tz=UTC]",
    "data_fim": "timestamp[us, tz=UTC]",
    "source": "string",
    "extracted_at": "timestamp[us, tz=UTC]",
    "ingestion_run_id": "string",
}