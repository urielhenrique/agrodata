"""Testes unitários para parser INMET."""

from __future__ import annotations

from agrodata.pipelines.inmet.parser import (
    _calcular_hash_linha,
    _extrair_metadados_estacao,
    _parsear_altitude,
    _parsear_coordenada,
    filtrar_variaveis_relevantes,
    ler_csv_bruto,
    parser_csv_para_registros,
)
from agrodata.pipelines.inmet.schemas import VARIAVEIS_PERMITIDAS


class TestParserUtils:
    def test_calcular_hash_linha(self):
        linha = "2023-01-01;1200;10,5;..."
        hash1 = _calcular_hash_linha(linha)
        hash2 = _calcular_hash_linha(linha)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_parsear_coordenada_valida(self):
        assert _parsear_coordenada("-19,92") == -19.92
        assert _parsear_coordenada("0,0") == 0.0
        assert _parsear_coordenada("-43,93") == -43.93

    def test_parsear_coordenada_invalida(self):
        assert _parsear_coordenada("") is None
        assert _parsear_coordenada("abc") is None
        assert _parsear_coordenada(None) is None

    def test_parsear_altitude_valida(self):
        assert _parsear_altitude("852,0") == 852.0
        assert _parsear_altitude("0,0") == 0.0

    def test_parsear_altitude_invalida(self):
        assert _parsear_altitude("") is None
        assert _parsear_altitude("abc") is None


class TestExtrairMetadados:
    def test_extrair_metadados_completo(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;10,5;30,5;20,1
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        meta = _extrair_metadados_estacao(csv_path)

        assert meta["regiao"] == "Sudeste"
        assert meta["uf"] == "MG"
        assert meta["station_name"] == "BELO HORIZONTE"
        assert meta["wmo_id"] == "83337"
        assert meta["latitude"] == "-19,92"
        assert meta["longitude"] == "-43,93"
        assert meta["altitude"] == "852,0"

    def test_extrair_metadados_incompleto(self, tmp_path):
        csv_content = """UF;MG
Estação;TESTE
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm)
2023-01-01;1200;10,5
"""
        csv_path = tmp_path / "A999.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        meta = _extrair_metadados_estacao(csv_path)

        assert meta["uf"] == "MG"
        assert meta["station_name"] == "TESTE"
        assert "wmo_id" not in meta


class TestLerCSVBruto:
    def test_ler_csv_com_dados(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;10,5;30,5;20,1
2023-01-01;1300;0,0;31,0;20,5
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        df, hashes, linhas = ler_csv_bruto(csv_path)

        assert len(df) == 2
        assert len(hashes) == 2
        assert len(linhas) == 2
        assert "Data" in df.columns
        assert "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)" in df.columns

    def test_ler_csv_vazio_apenas_header(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm)
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        df, hashes, linhas = ler_csv_bruto(csv_path)

        assert len(df) == 0
        assert len(hashes) == 0
        assert len(linhas) == 0

    def test_ler_csv_com_missing_9999(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;-9999;30,5
2023-01-01;1300;10,5;-9999
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        df, _, _ = ler_csv_bruto(csv_path)

        assert len(df) == 2
        assert df.iloc[0]["PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"] == "-9999"
        assert df.iloc[1]["TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)"] == "-9999"


class TestFiltrarVariaveis:
    def test_filtrar_variaveis_relevantes(self):
        import pandas as pd

        df = pd.DataFrame({
            "Data": ["2023-01-01"],
            "Hora UTC": ["1200"],
            "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": ["10,5"],
            "TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)": ["30,5"],
            "TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)": ["20,1"],
            "UMIDADE RELATIVA DO AR, HORÁRIA (%)": ["60"],
        })

        resultado = filtrar_variaveis_relevantes(df)

        assert "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)" in resultado.columns
        assert "TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)" in resultado.columns
        assert "TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)" in resultado.columns
        assert "UMIDADE RELATIVA DO AR, HORÁRIA (%)" not in resultado.columns


class TestParserCSVParaRegistros:
    def test_parser_gera_registros_corretos(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C);TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
2023-01-01;1200;10,5;30,5;20,1
2023-01-01;1300;0,0;31,0;20,5
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        registros = list(parser_csv_para_registros(csv_path, "2023-01-01T00:00:00", "run-001"))

        assert len(registros) == 6  # 2 timestamps x 3 variáveis

        vars_encontradas = {r["variable"] for r in registros}
        assert vars_encontradas == VARIAVEIS_PERMITIDAS

        for r in registros:
            assert r["station_id"] == "A808"
            assert r["source"] == "INMET_BDMEP"
            assert r["ingestion_run_id"] == "run-001"
            assert r["raw_row_hash"] != ""
            assert "_station_meta" in r

    def test_parser_missing_vira_none(self, tmp_path):
        csv_content = """Região;Sudeste
UF;MG
Estação;BELO HORIZONTE
Código (WMO);83337
Latitude;-19,92
Longitude;-43,93
Altitude;852,0
Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm)
2023-01-01;1200;-9999
"""
        csv_path = tmp_path / "A808.CSV"
        csv_path.write_text(csv_content, encoding="latin-1")

        registros = list(parser_csv_para_registros(csv_path, "2023-01-01T00:00:00", "run-001"))

        assert len(registros) == 1
        assert registros[0]["value"] is None
        assert registros[0]["quality_flag"] == "missing"