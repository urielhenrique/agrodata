"""Persistência de dados INMET em formato Parquet (PyArrow)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from agrodata.pipelines.inmet.schemas import (
    COLUNAS_OBSERVACAO,
    COLUNAS_STATION,
    ObservacaoHoraria,
    StationDimension,
)

SCHEMA_OBSERVACAO = pa.schema([
    pa.field("station_id", pa.string()),
    pa.field("datetime", pa.timestamp("us", tz="UTC")),
    pa.field("variable", pa.string()),
    pa.field("value", pa.float64()),
    pa.field("source", pa.string()),
    pa.field("extracted_at", pa.timestamp("us", tz="UTC")),
    pa.field("raw_row_hash", pa.string()),
    pa.field("ingestion_run_id", pa.string()),
    pa.field("quality_flag", pa.string()),
])

SCHEMA_STATION = pa.schema([
    pa.field("station_id", pa.string()),
    pa.field("wmo_id", pa.string()),
    pa.field("name", pa.string()),
    pa.field("uf", pa.string()),
    pa.field("latitude", pa.float64()),
    pa.field("longitude", pa.float64()),
    pa.field("altitude", pa.float64()),
    pa.field("data_inicio", pa.timestamp("us", tz="UTC")),
    pa.field("data_fim", pa.timestamp("us", tz="UTC")),
    pa.field("source", pa.string()),
    pa.field("extracted_at", pa.timestamp("us", tz="UTC")),
    pa.field("ingestion_run_id", pa.string()),
])


def _observacoes_para_dataframe(observacoes: list[ObservacaoHoraria]) -> pd.DataFrame:
    if not observacoes:
        return pd.DataFrame(columns=list(COLUNAS_OBSERVACAO.keys()))

    dados = [obs.model_dump() for obs in observacoes]
    df = pd.DataFrame(dados)

    colunas_ordem = list(COLUNAS_OBSERVACAO.keys())
    df = df[colunas_ordem]

    for col in ["station_id", "variable", "source", "raw_row_hash", "ingestion_run_id", "quality_flag"]:
        df[col] = df[col].astype("string")

    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["extracted_at"] = pd.to_datetime(df["extracted_at"], utc=True)

    df["value"] = df["value"].astype("float64")

    return df


def _stations_para_dataframe(stations: list[StationDimension]) -> pd.DataFrame:
    if not stations:
        return pd.DataFrame(columns=list(COLUNAS_STATION.keys()))

    dados = [s.model_dump() for s in stations]
    df = pd.DataFrame(dados)

    colunas_ordem = list(COLUNAS_STATION.keys())
    df = df[colunas_ordem]

    for col in ["station_id", "wmo_id", "name", "uf", "source", "ingestion_run_id"]:
        df[col] = df[col].astype("string")

    df["latitude"] = df["latitude"].astype("float64")
    df["longitude"] = df["longitude"].astype("float64")
    df["altitude"] = df["altitude"].astype("float64")

    df["data_inicio"] = pd.to_datetime(df["data_inicio"], utc=True)
    df["data_fim"] = pd.to_datetime(df["data_fim"], utc=True)
    df["extracted_at"] = pd.to_datetime(df["extracted_at"], utc=True)

    return df


def salvar_observations(
    observacoes: list[ObservacaoHoraria],
    raiz_processed: Path,
    ano: int,
    uf: str = "MG",
) -> Path:
    """Salva observações em Parquet particionado por year/uf."""
    df = _observacoes_para_dataframe(observacoes)

    if df.empty:
        return raiz_processed

    caminho = raiz_processed / "inmet" / "observations_hourly" / f"year={ano}" / f"uf={uf}"
    caminho.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, schema=SCHEMA_OBSERVACAO, preserve_index=False)

    pq.write_table(
        table,
        caminho / "part-0.parquet",
        compression="snappy",
        use_dictionary=True,
    )

    return caminho


def salvar_stations(
    stations: list[StationDimension],
    raiz_processed: Path,
) -> Path:
    """Salva dimensão de estações em Parquet."""
    df = _stations_para_dataframe(stations)

    if df.empty:
        return raiz_processed

    caminho = raiz_processed / "inmet" / "stations"
    caminho.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, schema=SCHEMA_STATION, preserve_index=False)

    pq.write_table(
        table,
        caminho / "stations.parquet",
        compression="snappy",
        use_dictionary=True,
    )

    return caminho


def carregar_observations(caminho: Path) -> pd.DataFrame:
    """Carrega observações de um diretório Parquet particionado."""
    return pd.read_parquet(caminho, engine="pyarrow")


def carregar_stations(caminho: Path) -> pd.DataFrame:
    """Carrega dimensão de estações."""
    return pd.read_parquet(caminho, engine="pyarrow")