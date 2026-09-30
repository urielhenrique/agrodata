"""Catálogo de estações INMET/BDMEP."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

from agrodata.pipelines.inmet.parser import (
    obter_metadados_estacao,
)
from agrodata.pipelines.inmet.schemas import StationDimension


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


def listar_estacoes_zip(zip_path: Path) -> list[str]:
    """Lista códigos de estações presentes no ZIP (nomes dos arquivos CSV)."""
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as zf:
        csvs = [name for name in zf.namelist() if name.upper().endswith(".CSV")]
        return [Path(name).stem for name in csvs]


def extrair_metadados_todas_estacoes(zip_path: Path, destino_temp: Path) -> dict[str, dict]:
    """Extrai metadados de todas as estações no ZIP a partir dos CSVs já extraídos."""
    metadados = {}
    csvs = [f for f in destino_temp.iterdir() if f.suffix.upper() == ".CSV"]
    for csv_path in csvs:
        meta = obter_metadados_estacao(csv_path)
        station_id = csv_path.stem
        metadados[station_id] = meta
    return metadados


def filtrar_estacoes_uf(metadados: dict[str, dict], uf: str = "MG") -> dict[str, dict]:
    """Filtra estações por UF."""
    return {sid: meta for sid, meta in metadados.items() if meta.get("uf") == uf}


def construir_station_dimension(
    metadados: dict[str, dict],
    extracted_at,
    ingestion_run_id: str,
) -> list[StationDimension]:
    """Constrói lista de StationDimension a partir dos metadados."""
    stations: list[StationDimension] = []

    for station_id, meta in metadados.items():
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

    return stations


def obter_estacoes_validas_mg(zip_path: Path, destino_temp: Path) -> tuple[set[str], list[StationDimension]]:
    """Retorna set de station_ids válidas de MG e suas dimensões."""
    from datetime import datetime

    metadados = extrair_metadados_todas_estacoes(zip_path, destino_temp)
    metadados_mg = filtrar_estacoes_uf(metadados, "MG")

    extracted_at = datetime.now(UTC)
    ingestion_run_id = "catalog"

    stations = construir_station_dimension(metadados_mg, extracted_at, ingestion_run_id)
    station_ids = {s.station_id for s in stations}

    return station_ids, stations