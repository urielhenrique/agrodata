"""Testes unitários para transform INMET."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from agrodata.pipelines.inmet.schemas import ObservacaoHoraria, StationDimension
from agrodata.pipelines.inmet.transform import (
    _validar_faixa_precipitacao,
    _validar_faixa_temperatura,
    construir_dim_station,
    gerar_ingestion_run_id,
    transformar_registros,
)


class TestGerarIngestionRunId:
    def test_gera_uuid_valido(self):
        run_id = gerar_ingestion_run_id()
        assert isinstance(run_id, str)
        assert len(run_id) == 36
        uuid4_obj = uuid4()
        assert run_id != str(uuid4_obj)


class TestValidarFaixas:
    def test_temperatura_valida(self):
        assert _validar_faixa_temperatura(25.0) == "valid"
        assert _validar_faixa_temperatura(-10.0) == "valid"
        assert _validar_faixa_temperatura(40.0) == "valid"
        assert _validar_faixa_temperatura(None) == "valid"

    def test_temperatura_fora_faixa_baixa(self):
        assert _validar_faixa_temperatura(-60.0) == "out_of_range"

    def test_temperatura_fora_faixa_alta(self):
        assert _validar_faixa_temperatura(70.0) == "out_of_range"

    def test_precipitacao_valida(self):
        assert _validar_faixa_precipitacao(10.0) == "valid"
        assert _validar_faixa_precipitacao(0.0) == "valid"
        assert _validar_faixa_precipitacao(None) == "valid"

    def test_precipitacao_negativa(self):
        assert _validar_faixa_precipitacao(-5.0) == "out_of_range"

    def test_precipitacao_extrema(self):
        assert _validar_faixa_precipitacao(600.0) == "suspect"


class TestTransformarRegistros:
    def test_transformar_registros_basico(self):
        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        def gen():
            yield {
                "station_id": "A808",
                "datetime": datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                "variable": "precipitacao",
                "value": 10.5,
                "source": "INMET_BDMEP",
                "extracted_at": extracted_at.isoformat(),
                "raw_row_hash": "hash1",
                "ingestion_run_id": ingestion_run_id,
                "quality_flag": "valid",
                "_station_meta": {"uf": "MG", "station_name": "BH", "latitude": "-19,92", "longitude": "-43,93", "altitude": "852,0"},
            }
            yield {
                "station_id": "A808",
                "datetime": datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                "variable": "temp_max",
                "value": 30.5,
                "source": "INMET_BDMEP",
                "extracted_at": extracted_at.isoformat(),
                "raw_row_hash": "hash2",
                "ingestion_run_id": ingestion_run_id,
                "quality_flag": "valid",
                "_station_meta": {"uf": "MG", "station_name": "BH", "latitude": "-19,92", "longitude": "-43,93", "altitude": "852,0"},
            }

        observacoes, estacoes_meta = transformar_registros(gen(), extracted_at, ingestion_run_id)

        assert len(observacoes) == 2
        assert all(isinstance(o, ObservacaoHoraria) for o in observacoes)
        assert len(estacoes_meta) == 1

    def test_transformar_missing_mantem_none(self):
        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        def gen():
            yield {
                "station_id": "A808",
                "datetime": datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                "variable": "precipitacao",
                "value": None,
                "source": "INMET_BDMEP",
                "extracted_at": extracted_at.isoformat(),
                "raw_row_hash": "hash1",
                "ingestion_run_id": ingestion_run_id,
                "quality_flag": "missing",
                "_station_meta": {"uf": "MG", "station_name": "BH", "latitude": "-19,92", "longitude": "-43,93", "altitude": "852,0"},
            }

        observacoes, _ = transformar_registros(gen(), extracted_at, ingestion_run_id)

        assert len(observacoes) == 1
        assert observacoes[0].value is None
        assert observacoes[0].quality_flag == "missing"


class TestConstruirDimStation:
    def test_construir_station_dimension(self):
        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        estacoes_meta = {
            "A808": {
                "uf": "MG",
                "station_name": "BELO HORIZONTE",
                "wmo_id": "83337",
                "latitude": "-19,92",
                "longitude": "-43,93",
                "altitude": "852,0",
            },
            "A821": {
                "uf": "MG",
                "station_name": "JUIZ DE FORA",
                "latitude": "-21,76",
                "longitude": "-43,35",
                "altitude": "900,0",
            },
        }

        stations = construir_dim_station(estacoes_meta, extracted_at, ingestion_run_id)

        assert len(stations) == 2
        assert all(isinstance(s, StationDimension) for s in stations)
        assert {s.station_id for s in stations} == {"A808", "A821"}
        assert stations[0].uf == "MG"
        assert stations[0].latitude == -19.92

    def test_estacao_sem_coordenadas_pulada(self):
        extracted_at = datetime.now(UTC)
        ingestion_run_id = "run-test"

        estacoes_meta = {
            "A808": {"uf": "MG", "station_name": "BH"},
            "A821": {"uf": "MG", "station_name": "JF", "latitude": "-21,76", "longitude": "-43,35"},
        }

        stations = construir_dim_station(estacoes_meta, extracted_at, ingestion_run_id)

        assert len(stations) == 1
        assert stations[0].station_id == "A821"