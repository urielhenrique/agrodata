"""Testes unitários para load INMET."""

from __future__ import annotations

from datetime import UTC, datetime

from agrodata.pipelines.inmet.load import (
    carregar_observations,
    carregar_stations,
    salvar_observations,
    salvar_stations,
)
from agrodata.pipelines.inmet.schemas import ObservacaoHoraria, StationDimension


class TestSalvarObservations:
    def test_salvar_observations_roundtrip(self, tmp_path):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.5,
                extracted_at=datetime.now(UTC),
                raw_row_hash="hash1",
                ingestion_run_id="run-1",
            ),
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 13, 0, tzinfo=UTC),
                variable="temp_max",
                value=30.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="hash2",
                ingestion_run_id="run-1",
            ),
        ]

        caminho = salvar_observations(obs, tmp_path, 2023, "MG")

        assert caminho.exists()
        assert (caminho / "part-0.parquet").exists()

        df = carregar_observations(caminho)

        assert len(df) == 2
        assert list(df.columns) == [
            "station_id", "datetime", "variable", "value",
            "source", "extracted_at", "raw_row_hash", "ingestion_run_id", "quality_flag"
        ]
        assert df["station_id"].tolist() == ["A808", "A808"]
        assert df["variable"].tolist() == ["precipitacao", "temp_max"]
        assert df["value"].tolist() == [10.5, 30.0]

    def test_salvar_observations_vazio(self, tmp_path):
        caminho = salvar_observations([], tmp_path, 2023, "MG")
        assert caminho == tmp_path

    def test_particionamento_ano_uf(self, tmp_path):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
            ),
        ]

        caminho = salvar_observations(obs, tmp_path, 2023, "MG")

        assert "year=2023" in str(caminho)
        assert "uf=MG" in str(caminho)


class TestSalvarStations:
    def test_salvar_stations_roundtrip(self, tmp_path):
        stations = [
            StationDimension(
                station_id="A808",
                wmo_id="83337",
                name="BELO HORIZONTE",
                uf="MG",
                latitude=-19.92,
                longitude=-43.93,
                altitude=852.0,
                extracted_at=datetime.now(UTC),
                ingestion_run_id="run-1",
            ),
        ]

        caminho = salvar_stations(stations, tmp_path)

        assert caminho.exists()
        assert (caminho / "stations.parquet").exists()

        df = carregar_stations(caminho / "stations.parquet")

        assert len(df) == 1
        assert df["station_id"].tolist() == ["A808"]
        assert df["name"].tolist() == ["BELO HORIZONTE"]
        assert df["uf"].tolist() == ["MG"]
        assert df["latitude"].tolist() == [-19.92]

    def test_salvar_stations_vazio(self, tmp_path):
        caminho = salvar_stations([], tmp_path)
        assert caminho == tmp_path