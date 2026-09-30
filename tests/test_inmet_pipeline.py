"""Testes unitários para pipeline INMET."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

from agrodata.pipelines.inmet.pipeline import (
    ConfigPipelineINMET,
    executar_pipeline,
)


class TestConfigPipelineINMET:
    def test_config_defaults(self):
        config = ConfigPipelineINMET()
        assert config.ano == 2023
        assert config.uf == "MG"
        assert config.max_estacoes is None
        assert config.reutilizar_raw is True

    def test_config_ano_invalido_baixo(self):
        with pytest.raises(ValueError):
            ConfigPipelineINMET(ano=1999)

    def test_config_ano_invalido_alto(self):
        with pytest.raises(ValueError):
            ConfigPipelineINMET(ano=2031)


class TestExecutarPipeline:
    @patch("agrodata.pipelines.inmet.pipeline.INMETClient")
    @patch("agrodata.pipelines.inmet.pipeline.extrair_zip")
    @patch("agrodata.pipelines.inmet.pipeline.extrair_metadados_todas_estacoes")
    @patch("agrodata.pipelines.inmet.pipeline.parser_csv_para_registros")
    @patch("agrodata.pipelines.inmet.pipeline.transformar_registros")
    @patch("agrodata.pipelines.inmet.pipeline.verificar_qualidade")
    @patch("agrodata.pipelines.inmet.pipeline.salvar_observations")
    @patch("agrodata.pipelines.inmet.pipeline.salvar_stations")
    def test_pipeline_executa_com_mocks(
        self,
        mock_salvar_stations,
        mock_salvar_obs,
        mock_verificar_qualidade,
        mock_transformar,
        mock_parser,
        mock_extrair_meta,
        mock_extrair_zip,
        mock_client_class,
        tmp_path,
    ):
        # Setup mocks
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_extrair_zip.return_value = [tmp_path / "A808.CSV", tmp_path / "A821.CSV"]

        mock_extrair_meta.return_value = {
            "A808": {"uf": "MG", "station_name": "BH", "latitude": "-19,92", "longitude": "-43,93", "altitude": "852,0"},
            "A821": {"uf": "MG", "station_name": "JF", "latitude": "-21,76", "longitude": "-43,35", "altitude": "900,0"},
        }

        mock_parser.return_value = iter([
            {
                "station_id": "A808",
                "datetime": "2023-01-01T12:00:00+00:00",
                "variable": "precipitacao",
                "value": 10.0,
                "source": "INMET_BDMEP",
                "extracted_at": "2023-01-01T00:00:00",
                "raw_row_hash": "h1",
                "ingestion_run_id": "run-1",
                "quality_flag": "valid",
                "_station_meta": {},
            }
        ])

        from datetime import datetime

        from agrodata.pipelines.inmet.schemas import ObservacaoHoraria

        mock_transformar.return_value = (
            [
                ObservacaoHoraria(
                    station_id="A808",
                    datetime=datetime(2023, 1, 1, 12, 0, tzinfo=UTC),
                    variable="precipitacao",
                    value=10.0,
                    extracted_at=datetime.now(UTC),
                    raw_row_hash="h1",
                    ingestion_run_id="run-1",
                )
            ],
            {"A808": {}},
        )

        from agrodata.pipelines.inmet.quality import QualityReport
        mock_verificar_qualidade.return_value = QualityReport(
            total_registros=1,
            contagem_por_flag={"valid": 1},
            contagem_por_regra={},
            duplicidades_pk=0,
            gaps_temporais_maiores_24h=0,
            estacoes_sem_metadata=0,
            erros=0,
            warnings=0,
            valido=True,
        )

        mock_salvar_obs.return_value = tmp_path / "obs"
        mock_salvar_stations.return_value = tmp_path / "stations"

        config = ConfigPipelineINMET(
            ano=2023,
            uf="MG",
            raiz_raw=tmp_path / "raw",
            raiz_processed=tmp_path / "processed",
            reutilizar_raw=True,
        )

        # Criar RAW fake
        raw_path = config.raiz_raw / "inmet" / "2023" / "BDMEP_2023.zip"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(b"fake zip")

        metricas = executar_pipeline(config, raiz=tmp_path)

        assert metricas.ano == 2023
        assert metricas.uf == "MG"
        assert metricas.estações_processadas == 2
        assert metricas.registros_normalizados == 1
        assert metricas.qualidade_valida is True
        assert metricas.ingestion_run_id != ""