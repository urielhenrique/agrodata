"""Testes unitários para schemas INMET."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agrodata.pipelines.inmet.schemas import (
    VARIAVEIS_PERMITIDAS,
    ObservacaoHoraria,
    StationDimension,
)


class TestObservacaoHoraria:
    def test_criar_observacao_valida(self):
        obs = ObservacaoHoraria(
            station_id="A808",
            datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            variable="precipitacao",
            value=10.5,
            extracted_at=datetime.now(UTC),
            raw_row_hash="abc123",
            ingestion_run_id="run-001",
        )
        assert obs.station_id == "A808"
        assert obs.variable == "precipitacao"
        assert obs.value == 10.5
        assert obs.quality_flag == "valid"
        assert obs.source == "INMET_BDMEP"

    def test_criar_observacao_missing_value(self):
        obs = ObservacaoHoraria(
            station_id="A808",
            datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            variable="temp_max",
            value=None,
            extracted_at=datetime.now(UTC),
            raw_row_hash="abc123",
            ingestion_run_id="run-001",
            quality_flag="missing",
        )
        assert obs.value is None
        assert obs.quality_flag == "missing"

    def test_validar_variavel_invalida(self):
        with pytest.raises(ValueError):
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="umidade",
                value=50.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="abc123",
                ingestion_run_id="run-001",
            )

    def test_parse_missing_minus_9999(self):
        obs = ObservacaoHoraria(
            station_id="A808",
            datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            variable="precipitacao",
            value=-9999,
            extracted_at=datetime.now(UTC),
            raw_row_hash="abc123",
            ingestion_run_id="run-001",
        )
        assert obs.value is None

    def test_parse_missing_string(self):
        obs = ObservacaoHoraria(
            station_id="A808",
            datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
            variable="precipitacao",
            value="-9999",
            extracted_at=datetime.now(UTC),
            raw_row_hash="abc123",
            ingestion_run_id="run-001",
        )
        assert obs.value is None


class TestStationDimension:
    def test_criar_station_valida(self):
        station = StationDimension(
            station_id="A808",
            wmo_id="83337",
            name="BELO HORIZONTE",
            uf="MG",
            latitude=-19.92,
            longitude=-43.93,
            altitude=852.0,
            extracted_at=datetime.now(UTC),
            ingestion_run_id="run-001",
        )
        assert station.station_id == "A808"
        assert station.uf == "MG"
        assert station.latitude == -19.92

    def test_latitude_fora_faixa(self):
        with pytest.raises(ValueError):
            StationDimension(
                station_id="A808",
                name="TESTE",
                uf="MG",
                latitude=95.0,
                longitude=-43.93,
                extracted_at=datetime.now(UTC),
                ingestion_run_id="run-001",
            )

    def test_longitude_fora_faixa(self):
        with pytest.raises(ValueError):
            StationDimension(
                station_id="A808",
                name="TESTE",
                uf="MG",
                latitude=-19.92,
                longitude=-200.0,
                extracted_at=datetime.now(UTC),
                ingestion_run_id="run-001",
            )


class TestVariaveisPermitidas:
    def test_variaveis_permitidas_corretas(self):
        assert "precipitacao" in VARIAVEIS_PERMITIDAS
        assert "temp_max" in VARIAVEIS_PERMITIDAS
        assert "temp_min" in VARIAVEIS_PERMITIDAS
        assert len(VARIAVEIS_PERMITIDAS) == 3