"""Testes unitários para station_catalog INMET."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from agrodata.pipelines.inmet.station_catalog import (
    _parsear_altitude,
    _parsear_coordenada,
    construir_station_dimension,
    filtrar_estacoes_uf,
    listar_estacoes_zip,
)


class TestStationCatalogUtils:
    def test_parsear_coordenada(self):
        assert _parsear_coordenada("-19,92") == -19.92
        assert _parsear_coordenada("0,0") == 0.0
        assert _parsear_coordenada("") is None
        assert _parsear_coordenada("invalid") is None

    def test_parsear_altitude(self):
        assert _parsear_altitude("852,0") == 852.0
        assert _parsear_altitude("") is None
        assert _parsear_altitude("invalid") is None


class TestFiltrarEstacoesUF:
    def test_filtrar_mg(self):
        metadados = {
            "A808": {"uf": "MG", "station_name": "BH"},
            "A821": {"uf": "MG", "station_name": "JF"},
            "A101": {"uf": "SP", "station_name": "SP"},
        }

        resultado = filtrar_estacoes_uf(metadados, "MG")

        assert len(resultado) == 2
        assert "A808" in resultado
        assert "A821" in resultado
        assert "A101" not in resultado


class TestConstruirStationDimension:
    def test_construir_stations(self):
        metadados = {
            "A808": {
                "uf": "MG",
                "station_name": "BELO HORIZONTE",
                "wmo_id": "83337",
                "latitude": "-19,92",
                "longitude": "-43,93",
                "altitude": "852,0",
            },
        }

        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        stations = construir_station_dimension(metadados, extracted_at, ingestion_run_id)

        assert len(stations) == 1
        s = stations[0]
        assert s.station_id == "A808"
        assert s.name == "BELO HORIZONTE"
        assert s.uf == "MG"
        assert s.latitude == -19.92
        assert s.longitude == -43.93
        assert s.altitude == 852.0

    def test_estacao_sem_coords_pulada(self):
        metadados = {
            "A808": {"uf": "MG", "station_name": "BH"},
            "A821": {"uf": "MG", "station_name": "JF", "latitude": "-21,76", "longitude": "-43,35"},
        }

        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        stations = construir_station_dimension(metadados, extracted_at, ingestion_run_id)

        assert len(stations) == 1
        assert stations[0].station_id == "A821"


class TestListarEstacoesZip:
    @patch("zipfile.ZipFile")
    def test_listar_estacoes(self, mock_zipfile):
        mock_zf = MagicMock()
        mock_zf.namelist.return_value = ["A808.CSV", "A821.CSV", "README.txt"]
        mock_zipfile.return_value.__enter__.return_value = mock_zf

        resultado = listar_estacoes_zip(Path("dummy.zip"))

        assert resultado == ["A808", "A821"]