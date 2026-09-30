"""Testes unitários para quality INMET."""

from __future__ import annotations

from datetime import UTC, datetime

from agrodata.pipelines.inmet.quality import verificar_qualidade
from agrodata.pipelines.inmet.schemas import ObservacaoHoraria


class TestVerificarQualidade:
    def test_todos_validos(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 13, 0, tzinfo=UTC),
                variable="temp_max",
                value=30.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h2",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.total_registros == 2
        assert report.erros == 0
        assert report.warnings == 0
        assert report.valido is True
        assert report.contagem_por_flag["valid"] == 2

    def test_missing_contado(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=None,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="missing",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.contagem_por_regra["missing"] == 1
        assert report.contagem_por_flag["missing"] == 1

    def test_precipitacao_negativa_warning(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=-5.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="out_of_range",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.contagem_por_regra["precipitacao_negativa"] == 1
        assert report.warnings == 1
        assert report.erros == 0
        assert report.valido is True  # warnings não invalidam

    def test_temp_max_menor_min_warning(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="temp_max",
                value=20.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="temp_min",
                value=25.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h2",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.contagem_por_regra["temp_max_menor_min"] == 1
        assert report.warnings == 1

    def test_temperatura_fora_faixa_erro(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="temp_max",
                value=70.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="out_of_range",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.contagem_por_regra["temperatura_fora_faixa"] == 1
        assert report.erros == 1
        assert report.valido is False

    def test_precipitacao_extrema_suspect(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=600.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="suspect",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.contagem_por_regra["precipitacao_extrema"] == 1
        assert report.contagem_por_flag["suspect"] == 1
        assert report.warnings == 1

    def test_duplicidade_pk_erro(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h2",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.duplicidades_pk == 1
        assert report.erros == 1
        assert report.valido is False

    def test_gaps_temporais_24h(self):
        obs = [
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
            ObservacaoHoraria(
                station_id="A808",
                datetime=datetime(2023, 1, 3, 12, 0, tzinfo=UTC),  # gap de 48h
                variable="precipitacao",
                value=5.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h2",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.gaps_temporais_maiores_24h == 1
        assert report.warnings == 1

    def test_estacao_sem_metadata_warning(self):
        obs = [
            ObservacaoHoraria(
                station_id="A999",  # não está em estacoes_conhecidas
                datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                variable="precipitacao",
                value=10.0,
                extracted_at=datetime.now(UTC),
                raw_row_hash="h1",
                ingestion_run_id="run-1",
                quality_flag="valid",
            ),
        ]

        report = verificar_qualidade(obs, {"A808"})

        assert report.estacoes_sem_metadata == 1
        assert report.warnings == 1

    def test_lista_vazia(self):
        report = verificar_qualidade([], set())

        assert report.total_registros == 0
        assert report.erros == 0
        assert report.warnings == 0
        assert report.valido is True

    def test_quality_report_to_dict(self):
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

        report = verificar_qualidade(obs, {"A808"})
        d = report.to_dict()

        assert isinstance(d, dict)
        assert "total_registros" in d
        assert "contagem_por_flag" in d
        assert "contagem_por_regra" in d
        assert d["valido"] is True