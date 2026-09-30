"""Teste de integração E2E para pipeline INMET."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from agrodata.pipelines.inmet.pipeline import ConfigPipelineINMET, executar_pipeline


@pytest.fixture
def sample_zip_path(tmp_path) -> Path:
    """Cria um ZIP de teste pequeno com 2 estações MG."""
    import zipfile

    csv_a808 = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;0000;0,0;25,5;18,2
2023-01-01;0100;0,0;24,8;17,9
2023-01-01;0200;0,0;24,1;17,5
2023-01-01;0300;0,0;23,6;17,2
2023-01-01;0400;0,0;23,2;17,0
2023-01-01;0500;0,0;22,9;16,8
2023-01-01;0600;0,0;22,7;16,7
2023-01-01;0700;0,0;22,8;16,8
2023-01-01;0800;0,0;23,5;17,2
2023-01-01;0900;0,0;25,1;18,5
2023-01-01;1000;0,0;27,2;20,1
2023-01-01;1100;0,0;28,8;21,5
2023-01-01;1200;0,0;30,1;22,8
2023-01-01;1300;0,0;30,8;23,5
2023-01-01;1400;0,0;31,2;24,0
2023-01-01;1500;0,0;31,0;24,2
2023-01-01;1600;0,0;30,5;24,1
2023-01-01;1700;0,0;29,8;23,5
2023-01-01;1800;0,0;28,5;22,2
2023-01-01;1900;0,0;27,0;20,8
2023-01-01;2000;0,0;25,8;19,5
2023-01-01;2100;0,0;25,0;18,8
2023-01-01;2200;0,0;24,5;18,2
2023-01-01;2300;0,0;24,1;17,9
"""

    csv_a821 = """Região;Sudeste
UF;MG
Estação;JUIZ DE FORA
Código (WMO);83585
Latitude;-21,76
Longitude;-43,35
Altitude;900,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;0000;0,0;24,2;16,8
2023-01-01;0100;0,0;23,5;16,2
2023-01-01;0200;0,0;22,9;15,8
2023-01-01;0300;0,0;22,4;15,5
2023-01-01;0400;0,0;22,0;15,2
2023-01-01;0500;0,0;21,8;15,0
2023-01-01;0600;0,0;21,6;14,9
2023-01-01;0700;0,0;21,8;15,0
2023-01-01;0800;0,0;22,5;15,5
2023-01-01;0900;0,0;24,1;16,8
2023-01-01;1000;0,0;26,2;18,2
2023-01-01;1100;0,0;27,8;19,5
2023-01-01;1200;0,0;29,1;20,8
2023-01-01;1300;0,0;29,8;21,5
2023-01-01;1400;0,0;30,2;22,0
2023-01-01;1500;0,0;30,0;22,2
2023-01-01;1600;0,0;29,5;22,1
2023-01-01;1700;0,0;28,8;21,5
2023-01-01;1800;0,0;27,5;20,2
2023-01-01;1900;0,0;26,0;18,8
2023-01-01;2000;0,0;24,8;17,5
2023-01-01;2100;0,0;24,0;16,8
2023-01-01;2200;0,0;23,5;16,2
2023-01-01;2300;0,0;23,1;15,9
"""

    zip_path = tmp_path / "BDMEP_2023.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("A808.CSV", csv_a808.encode("latin-1"))
        zf.writestr("A821.CSV", csv_a821.encode("latin-1"))

    return zip_path


class TestPipelineE2E:
    def test_pipeline_e2e_com_fixture(self, sample_zip_path, tmp_path):
        """Teste E2E completo com fixture ZIP local (sem internet)."""

        # Copiar fixture para local onde pipeline espera
        raw_dir = tmp_path / "raw" / "inmet" / "2023"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_zip = raw_dir / "BDMEP_2023.zip"
        raw_zip.write_bytes(sample_zip_path.read_bytes())

        config = ConfigPipelineINMET(
            ano=2023,
            uf="MG",
            raiz_raw=tmp_path / "raw",
            raiz_processed=tmp_path / "processed",
            reutilizar_raw=True,
            max_estacoes=2,
        )

        with patch("agrodata.pipelines.inmet.pipeline.INMETClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            metricas = executar_pipeline(config, raiz=tmp_path)

        assert metricas.ano == 2023
        assert metricas.uf == "MG"
        assert metricas.estações_processadas == 2
        assert metricas.estações_com_dados == 2
        assert metricas.registros_normalizados > 0
        assert metricas.qualidade_valida is True
        assert metricas.erros == 0

        # Verificar arquivos Parquet gerados
        obs_path = tmp_path / "processed" / "inmet" / "observations_hourly" / "year=2023" / "uf=MG"
        assert obs_path.exists()
        assert (obs_path / "part-0.parquet").exists()

        stations_path = tmp_path / "processed" / "inmet" / "stations" / "stations.parquet"
        assert stations_path.exists()

    def test_parquet_roundtrip(self, sample_zip_path, tmp_path):
        """Verifica que Parquet gerado pode ser lido corretamente."""
        import pandas as pd

        raw_dir = tmp_path / "raw" / "inmet" / "2023"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_zip = raw_dir / "BDMEP_2023.zip"
        raw_zip.write_bytes(sample_zip_path.read_bytes())

        config = ConfigPipelineINMET(
            ano=2023,
            uf="MG",
            raiz_raw=tmp_path / "raw",
            raiz_processed=tmp_path / "processed",
            reutilizar_raw=True,
            max_estacoes=2,
        )

        with patch("agrodata.pipelines.inmet.pipeline.INMETClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            executar_pipeline(config, raiz=tmp_path)

        # Ler e validar
        obs_df = pd.read_parquet(tmp_path / "processed" / "inmet" / "observations_hourly" / "year=2023" / "uf=MG")
        stations_df = pd.read_parquet(tmp_path / "processed" / "inmet" / "stations" / "stations.parquet")

        assert len(obs_df) > 0
        assert len(stations_df) == 2

        # Verificar tipos
        assert obs_df["station_id"].dtype == "string"
        assert obs_df["variable"].dtype == "string"
        assert obs_df["value"].dtype == "float64"
        assert pd.api.types.is_datetime64tz_dtype(obs_df["datetime"])

        assert stations_df["station_id"].dtype == "string"
        assert stations_df["latitude"].dtype == "float64"
        assert stations_df["longitude"].dtype == "float64"

        # Verificar variáveis
        vars_unicas = set(obs_df["variable"].unique())
        assert vars_unicas == {"precipitacao", "temp_max", "temp_min"}

        # Verificar estações
        stations_unicas = set(stations_df["station_id"].unique())
        assert stations_unicas == {"A808", "A821"}

    def test_pipeline_bloqueia_duplicidade(self, tmp_path):
        """E2E: duplicidade (station_id, datetime, variable) bloqueia persistência."""
        import zipfile

        from agrodata.pipelines.inmet.parser import parser_csv_para_registros
        from agrodata.pipelines.inmet.quality import verificar_qualidade
        from agrodata.pipelines.inmet.transform import transformar_registros

        csv_dup = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;0,0;25,5;18,2
2023-01-01;1200;0,0;25,5;18,2
"""

        raw_dir = tmp_path / "raw" / "inmet" / "2023"
        raw_dir.mkdir(parents=True, exist_ok=True)
        zip_path = raw_dir / "BDMEP_2023.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("A808.CSV", csv_dup.encode("latin-1"))

        # Prova direta de detecção (sem pipeline): quality identifica duplicidade.
        csv_path = tmp_path / "A808_dup.CSV"
        csv_path.write_text(csv_dup, encoding="latin-1")
        extracted_at = datetime(2023, 1, 2, 0, 0, tzinfo=UTC)
        regs = list(parser_csv_para_registros(csv_path, extracted_at.isoformat(), "run-dup"))
        observacoes, _ = transformar_registros(iter(regs), extracted_at, "run-dup")
        report = verificar_qualidade(observacoes, {"A808"})
        assert report.duplicidades_pk > 0
        assert report.valido is False

        config = ConfigPipelineINMET(
            ano=2023,
            uf="MG",
            raiz_raw=tmp_path / "raw",
            raiz_processed=tmp_path / "processed",
            reutilizar_raw=True,
            max_estacoes=1,
        )

        with patch("agrodata.pipelines.inmet.pipeline.INMETClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            with pytest.raises(RuntimeError, match="Falha de qualidade"):
                executar_pipeline(config, raiz=tmp_path)

        # Nenhum Parquet válido da execução deve ter sido produzido.
        obs_part = (
            tmp_path
            / "processed"
            / "inmet"
            / "observations_hourly"
            / "year=2023"
            / "uf=MG"
            / "part-0.parquet"
        )
        assert not obs_part.exists()

    def test_timezone_utc_roundtrip(self, tmp_path):
        """E2E: Data=2023-01-01 Hora UTC=1200 → 2023-01-01 12:00:00+00:00."""
        from agrodata.pipelines.inmet.load import salvar_observations
        from agrodata.pipelines.inmet.parser import parser_csv_para_registros
        from agrodata.pipelines.inmet.transform import transformar_registros

        csv_single = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;1,5;28,4;19,7
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_single, encoding="latin-1")

        extracted_at = datetime(2023, 1, 2, 0, 0, tzinfo=UTC)
        ingestion_run_id = "run-tz-e2e"

        registros = list(
            parser_csv_para_registros(csv_path, extracted_at.isoformat(), ingestion_run_id)
        )
        assert len(registros) == 3
        esperado = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
        for reg in registros:
            assert reg["datetime"] == esperado
            assert reg["datetime"].tzinfo is not None

        observacoes, _ = transformar_registros(iter(registros), extracted_at, ingestion_run_id)
        assert len(observacoes) == 3
        for obs in observacoes:
            assert obs.datetime == esperado
            assert obs.datetime.tzinfo is not None

        caminho = salvar_observations(observacoes, tmp_path / "processed", 2023, "MG")
        df = pd.read_parquet(caminho)

        assert str(df["datetime"].dt.tz) == "UTC"
        linha = df[
            (df["station_id"] == "A808") & (df["variable"] == "precipitacao")
        ].iloc[0]
        assert linha["datetime"] == pd.Timestamp("2023-01-01 12:00:00+00:00")
        assert linha["datetime"].isoformat() == "2023-01-01T12:00:00+00:00"

    def test_raw_row_hash_deterministico(self, tmp_path):
        """Integração: mesma linha original → mesmo raw_row_hash."""
        import hashlib

        from agrodata.pipelines.inmet.parser import (
            ler_csv_bruto,
            parser_csv_para_registros,
        )
        from agrodata.pipelines.inmet.transform import transformar_registros

        csv_single = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;2,5;29,0;20,0
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_single, encoding="latin-1")

        _, hashes, linhas = ler_csv_bruto(csv_path)
        assert len(linhas) == 1
        linha_original = linhas[0]
        esperado = hashlib.sha256(linha_original.encode("latin-1")).hexdigest()
        assert hashes[0] == esperado

        extracted_at = datetime(2023, 1, 2, 0, 0, tzinfo=UTC)
        regs_exec1 = list(
            parser_csv_para_registros(csv_path, extracted_at.isoformat(), "run-hash-1")
        )
        regs_exec2 = list(
            parser_csv_para_registros(csv_path, extracted_at.isoformat(), "run-hash-2")
        )
        assert len(regs_exec1) == 3
        assert len(regs_exec2) == 3
        for reg in [*regs_exec1, *regs_exec2]:
            assert reg["raw_row_hash"] == esperado
        assert regs_exec1[0]["raw_row_hash"] == regs_exec2[0]["raw_row_hash"]

        observacoes, _ = transformar_registros(iter(regs_exec1), extracted_at, "run-hash-1")
        assert len(observacoes) == 3
        for obs in observacoes:
            assert obs.raw_row_hash == esperado