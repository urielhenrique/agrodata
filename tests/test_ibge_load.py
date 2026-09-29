"""Testes para a camada de persistência (load) do IBGE."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agrodata.pipelines.ibge.load import (
    COLUNAS_DATASET,
    COLUNAS_ORDEM,
    carregar_parquet,
    registros_para_dataframe,
    salvar_parquet,
)
from agrodata.pipelines.ibge.schemas import RegistroAgricola

# ---------------------------------------------------------------------------
# Fixtures de dados
# ---------------------------------------------------------------------------


@pytest.fixture()
def registro_simples() -> RegistroAgricola:
    """Registro agrícola simples para testes."""
    return RegistroAgricola(
        variavel_id="8331",
        variavel_nome="Área plantada ou destinada à colheita",
        variavel_unidade="Hectares",
        classificacao_id="782",
        classificacao_nome="Produto das lavouras temporárias e permanentes",
        categoria_codigo="40124",
        categoria_nome="Soja (em grão)",
        localidade_id="5103403",
        localidade_nome="Cuiabá (MT)",
        nivel_territorial_id="N6",
        nivel_territorial_nome="Município",
        periodo="2023",
        valor_bruto="790",
    )


@pytest.fixture()
def registro_valor_ausente() -> RegistroAgricola:
    """Registro com valor ausente ("-")."""
    return RegistroAgricola(
        variavel_id="8331",
        variavel_nome="Área plantada ou destinada à colheita",
        variavel_unidade="Hectares",
        classificacao_id="782",
        classificacao_nome="Produto das lavouras temporárias e permanentes",
        categoria_codigo="40124",
        categoria_nome="Soja (em grão)",
        localidade_id="3550308",
        localidade_nome="São Paulo (SP)",
        nivel_territorial_id="N6",
        nivel_territorial_nome="Município",
        periodo="2023",
        valor_bruto="-",
    )


@pytest.fixture()
def registro_valor_dois_pontos() -> RegistroAgricola:
    """Registro com valor ausente ("..")."""
    return RegistroAgricola(
        variavel_id="214",
        variavel_nome="Quantidade produzida",
        variavel_unidade="Toneladas",
        classificacao_id="782",
        classificacao_nome="Produto das lavouras temporárias e permanentes",
        categoria_codigo="40122",
        categoria_nome="Milho (em grão)",
        localidade_id="5103403",
        localidade_nome="Cuiabá (MT)",
        nivel_territorial_id="N6",
        nivel_territorial_nome="Município",
        periodo="2023",
        valor_bruto="..",
    )


@pytest.fixture()
def registro_valor_tres_pontos() -> RegistroAgricola:
    """Registro com valor ausente ("...")."""
    return RegistroAgricola(
        variavel_id="112",
        variavel_nome="Rendimento médio da produção",
        variavel_unidade="Quilogramas por Hectare",
        classificacao_id="782",
        classificacao_nome="Produto das lavouras temporárias e permanentes",
        categoria_codigo="40123",
        categoria_nome="Arroz (em grão)",
        localidade_id="5103403",
        localidade_nome="Cuiabá (MT)",
        nivel_territorial_id="N6",
        nivel_territorial_nome="Município",
        periodo="2023",
        valor_bruto="...",
    )


@pytest.fixture()
def registro_valor_float() -> RegistroAgricola:
    """Registro com valor numérico float."""
    return RegistroAgricola(
        variavel_id="112",
        variavel_nome="Rendimento médio da produção",
        variavel_unidade="Quilogramas por Hectare",
        classificacao_id="782",
        classificacao_nome="Produto das lavouras temporárias e permanentes",
        categoria_codigo="40124",
        categoria_nome="Soja (em grão)",
        localidade_id="5103403",
        localidade_nome="Cuiabá (MT)",
        nivel_territorial_id="N6",
        nivel_territorial_nome="Município",
        periodo="2023",
        valor_bruto="3400.5",
    )


@pytest.fixture()
def lista_registros(
    registro_simples: RegistroAgricola,
    registro_valor_ausente: RegistroAgricola,
) -> list[RegistroAgricola]:
    """Lista com múltiplos registros para testes."""
    return [registro_simples, registro_valor_ausente]


@pytest.fixture()
def lista_registros_completos(
    registro_simples: RegistroAgricola,
    registro_valor_ausente: RegistroAgricola,
    registro_valor_dois_pontos: RegistroAgricola,
    registro_valor_tres_pontos: RegistroAgricola,
    registro_valor_float: RegistroAgricola,
) -> list[RegistroAgricola]:
    """Lista completa com diferentes tipos de valores."""
    return [
        registro_simples,
        registro_valor_ausente,
        registro_valor_dois_pontos,
        registro_valor_tres_pontos,
        registro_valor_float,
    ]


# ---------------------------------------------------------------------------
# Testes: registros_para_dataframe
# ---------------------------------------------------------------------------


class TestRegistrosParaDataframe:
    """Testes para conversão de registros em DataFrame."""

    def test_retorna_dataframe(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert isinstance(df, pd.DataFrame)

    def test_quantidade_linhas(self, lista_registros: list) -> None:
        df = registros_para_dataframe(lista_registros)
        assert len(df) == 2

    def test_quantidade_colunas(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert df.shape[1] == 14

    def test_nomes_colunas(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert list(df.columns) == COLUNAS_ORDEM

    def test_colunas_esperadas(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        colunas_esperadas = {
            "variavel_id",
            "variavel_nome",
            "variavel_unidade",
            "classificacao_id",
            "classificacao_nome",
            "categoria_codigo",
            "categoria_nome",
            "localidade_id",
            "localidade_nome",
            "nivel_territorial_id",
            "nivel_territorial_nome",
            "periodo",
            "valor_bruto",
            "valor_numerico",
        }
        assert set(df.columns) == colunas_esperadas


# ---------------------------------------------------------------------------
# Testes: tipos das colunas
# ---------------------------------------------------------------------------


class TestTiposColunas:
    """Testes para verificação de tipos das colunas."""

    def test_ids_sao_string(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert str(df["variavel_id"].dtype) == "string"
        assert str(df["classificacao_id"].dtype) == "string"
        assert str(df["categoria_codigo"].dtype) == "string"
        assert str(df["localidade_id"].dtype) == "string"
        assert str(df["nivel_territorial_id"].dtype) == "string"

    def test_textos_sao_string(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert str(df["variavel_nome"].dtype) == "string"
        assert str(df["variavel_unidade"].dtype) == "string"
        assert str(df["classificacao_nome"].dtype) == "string"
        assert str(df["categoria_nome"].dtype) == "string"
        assert str(df["localidade_nome"].dtype) == "string"
        assert str(df["nivel_territorial_nome"].dtype) == "string"

    def test_periodo_e_string(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert str(df["periodo"].dtype) == "string"
        assert df["periodo"].iloc[0] == "2023"

    def test_valor_bruto_e_string(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert str(df["valor_bruto"].dtype) == "string"
        assert df["valor_bruto"].iloc[0] == "790"

    def test_valor_numerico_e_float(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert pd.api.types.is_float_dtype(df["valor_numerico"])
        assert df["valor_numerico"].iloc[0] == 790.0


# ---------------------------------------------------------------------------
# Testes: preservação de valores
# ---------------------------------------------------------------------------


class TestPreservacaoValores:
    """Testes para preservação de valores nos registros."""

    def test_valor_bruto_preservado(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert df["valor_bruto"].iloc[0] == "790"

    def test_valor_bruto_menos_preservado(
        self, registro_valor_ausente: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_ausente])
        assert df["valor_bruto"].iloc[0] == "-"

    def test_valor_numericoCalculado(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert df["valor_numerico"].iloc[0] == 790.0

    def test_valor_numerico_none_para_ausente(
        self, registro_valor_ausente: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_ausente])
        assert pd.isna(df["valor_numerico"].iloc[0])

    def test_valor_numerico_none_para_dois_pontos(
        self, registro_valor_dois_pontos: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_dois_pontos])
        assert pd.isna(df["valor_numerico"].iloc[0])

    def test_valor_numerico_none_para_tres_pontos(
        self, registro_valor_tres_pontos: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_tres_pontos])
        assert pd.isna(df["valor_numerico"].iloc[0])

    def test_valor_float_preservado(
        self, registro_valor_float: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_float])
        assert df["valor_numerico"].iloc[0] == 3400.5


# ---------------------------------------------------------------------------
# Testes: IDs como strings
# ---------------------------------------------------------------------------


class TestIdsStrings:
    """Testes para garantir que IDs permanecem como strings."""

    def test_localidade_id_nao_e_numero(
        self, registro_simples: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        localidade_id = df["localidade_id"].iloc[0]
        assert isinstance(localidade_id, str)
        assert localidade_id == "5103403"

    def test_variavel_id_nao_e_numero(
        self, registro_simples: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        variavel_id = df["variavel_id"].iloc[0]
        assert isinstance(variavel_id, str)
        assert variavel_id == "8331"

    def test_classificacao_id_nao_e_numero(
        self, registro_simples: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        classificacao_id = df["classificacao_id"].iloc[0]
        assert isinstance(classificacao_id, str)
        assert classificacao_id == "782"


# ---------------------------------------------------------------------------
# Testes: período
# ---------------------------------------------------------------------------


class TestPeriodo:
    """Testes para preservação do período."""

    def test_periodo_string(self, registro_simples: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_simples])
        assert df["periodo"].iloc[0] == "2023"
        assert isinstance(df["periodo"].iloc[0], str)


# ---------------------------------------------------------------------------
# Testes: valores ausentes preservados
# ---------------------------------------------------------------------------


class TestValoresAusentes:
    """Testes para preservação de valores ausentes."""

    def test_menos_preservado(self, registro_valor_ausente: RegistroAgricola) -> None:
        df = registros_para_dataframe([registro_valor_ausente])
        assert df["valor_bruto"].iloc[0] == "-"
        assert pd.isna(df["valor_numerico"].iloc[0])

    def test_dois_pontos_preservado(
        self, registro_valor_dois_pontos: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_dois_pontos])
        assert df["valor_bruto"].iloc[0] == ".."
        assert pd.isna(df["valor_numerico"].iloc[0])

    def test_tres_pontos_preservado(
        self, registro_valor_tres_pontos: RegistroAgricola
    ) -> None:
        df = registros_para_dataframe([registro_valor_tres_pontos])
        assert df["valor_bruto"].iloc[0] == "..."
        assert pd.isna(df["valor_numerico"].iloc[0])


# ---------------------------------------------------------------------------
# Testes: dataset vazio
# ---------------------------------------------------------------------------


class TestDatasetVazio:
    """Testes para DataFrame vazio."""

    def test_lista_vazia(self) -> None:
        df = registros_para_dataframe([])
        assert len(df) == 0
        assert df.shape[1] == 14
        assert list(df.columns) == COLUNAS_ORDEM


# ---------------------------------------------------------------------------
# Testes: salvar_parquet e carregar_parquet
# ---------------------------------------------------------------------------


class TestParquet:
    """Testes para gravação e leitura de Parquet."""

    def test_salvar_e_carregar(
        self, registro_simples: RegistroAgricola, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        caminho = tmp_path / "teste.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        assert caminho_salvo.exists()

        df_carregado = carregar_parquet(caminho_salvo)
        assert df_carregado.shape == df.shape
        assert list(df_carregado.columns) == list(df.columns)

    def test_dados_preservados_apos_roundtrip(
        self, registro_simples: RegistroAgricola, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        caminho = tmp_path / "roundtrip.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        df_carregado = carregar_parquet(caminho_salvo)

        # Verifica valores
        assert df_carregado["variavel_id"].iloc[0] == "8331"
        assert df_carregado["localidade_id"].iloc[0] == "5103403"
        assert df_carregado["periodo"].iloc[0] == "2023"
        assert df_carregado["valor_bruto"].iloc[0] == "790"
        assert df_carregado["valor_numerico"].iloc[0] == 790.0

    def test_tipos_preservados_apos_roundtrip(
        self, registro_simples: RegistroAgricola, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        caminho = tmp_path / "tipos.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        df_carregado = carregar_parquet(caminho_salvo)

        # IDs devem ser string
        assert df_carregado["variavel_id"].dtype == "string"
        assert df_carregado["localidade_id"].dtype == "string"

        # valor_numerico deve ser float
        assert pd.api.types.is_float_dtype(df_carregado["valor_numerico"])

    def test_valores_ausentes_apos_roundtrip(
        self, registro_valor_ausente: RegistroAgricola, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe([registro_valor_ausente])
        caminho = tmp_path / "ausentes.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        df_carregado = carregar_parquet(caminho_salvo)

        assert df_carregado["valor_bruto"].iloc[0] == "-"
        assert pd.isna(df_carregado["valor_numerico"].iloc[0])

    def test_multiplas_linhas_apos_roundtrip(
        self, lista_registros_completos: list, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe(lista_registros_completos)
        caminho = tmp_path / "multiplas.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        df_carregado = carregar_parquet(caminho_salvo)

        assert df_carregado.shape == (5, 14)

    def test_cria_diretorios_necessarios(
        self, registro_simples: RegistroAgricola, tmp_path: Path
    ) -> None:
        df = registros_para_dataframe([registro_simples])
        caminho = tmp_path / "subdir" / "pastas" / "teste.parquet"

        caminho_salvo = salvar_parquet(df, caminho)
        assert caminho_salvo.exists()


# ---------------------------------------------------------------------------
# Testes: COLUNAS_DATASET e COLUNAS_ORDEM
# ---------------------------------------------------------------------------


class TestMetadados:
    """Testes para constantes de metadados."""

    def test_colunas_dataset_tem_14_colunas(self) -> None:
        assert len(COLUNAS_DATASET) == 14

    def test_colunas_ordem_tem_14_colunas(self) -> None:
        assert len(COLUNAS_ORDEM) == 14

    def test_colunas_ordem_sao_subconjunto_de_colunas_dataset(self) -> None:
        assert set(COLUNAS_ORDEM) == set(COLUNAS_DATASET.keys())

    def test_ids_sao_string_no_dataset(self) -> None:
        ids = [
            "variavel_id",
            "classificacao_id",
            "categoria_codigo",
            "localidade_id",
            "nivel_territorial_id",
        ]
        for col in ids:
            assert COLUNAS_DATASET[col] == "string", f"{col} deveria ser string"

    def test_textos_sao_string_no_dataset(self) -> None:
        textos = [
            "variavel_nome",
            "variavel_unidade",
            "classificacao_nome",
            "categoria_nome",
            "localidade_nome",
            "nivel_territorial_nome",
            "periodo",
            "valor_bruto",
        ]
        for col in textos:
            assert COLUNAS_DATASET[col] == "string", f"{col} deveria ser string"

    def test_valor_numerico_e_float64_no_dataset(self) -> None:
        assert COLUNAS_DATASET["valor_numerico"] == "float64"
