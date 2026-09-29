"""Testes para as verificações de qualidade de dados do IBGE."""

from __future__ import annotations

import pandas as pd
import pytest

from agrodata.pipelines.ibge.load import COLUNAS_ORDEM
from agrodata.pipelines.ibge.quality import (
    CHAVE_LOGICA,
    ResultadoDuplicidade,
    ResultadoNulos,
    ResultadoPerfil,
    ResultadoSchema,
    ResultadoValoresEspeciais,
    ResultadoValoresNumericos,
    contar_valores_especiais,
    contar_valores_numericos,
    gerar_perfil,
    verificar_duplicidade,
    verificar_nulos,
    verificar_schema,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def df_valido() -> pd.DataFrame:
    """DataFrame válido com 3 registros."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", "8331", "214"],
            "variavel_nome": [
                "Área plantada",
                "Área plantada",
                "Quantidade produzida",
            ],
            "variavel_unidade": ["Hectares", "Hectares", "Toneladas"],
            "classificacao_id": ["782", "782", "782"],
            "classificacao_nome": ["Produto", "Produto", "Produto"],
            "categoria_codigo": ["40124", "40122", "40124"],
            "categoria_nome": ["Soja", "Milho", "Soja"],
            "localidade_id": ["5103403", "5103403", "5103403"],
            "localidade_nome": ["Cuiabá (MT)", "Cuiabá (MT)", "Cuiabá (MT)"],
            "nivel_territorial_id": ["N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município"],
            "periodo": ["2023", "2023", "2023"],
            "valor_bruto": ["790", "350", "2686"],
            "valor_numerico": [790.0, 350.0, 2686.0],
        }
    )


@pytest.fixture()
def df_com_nulos() -> pd.DataFrame:
    """DataFrame com valores nulos em colunas obrigatórias."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", None, "214"],
            "variavel_nome": ["Área plantada", "Área plantada", None],
            "variavel_unidade": ["Hectares", "Hectares", "Toneladas"],
            "classificacao_id": ["782", "782", "782"],
            "classificacao_nome": ["Produto", "Produto", "Produto"],
            "categoria_codigo": ["40124", "40124", None],
            "categoria_nome": ["Soja", "Soja", "Soja"],
            "localidade_id": ["5103403", "5103403", "5103403"],
            "localidade_nome": ["Cuiabá", "Cuiabá", "Cuiabá"],
            "nivel_territorial_id": ["N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município"],
            "periodo": ["2023", "2023", "2023"],
            "valor_bruto": ["790", "-", "2686"],
            "valor_numerico": [790.0, None, 2686.0],
        }
    )


@pytest.fixture()
def df_com_especiais() -> pd.DataFrame:
    """DataFrame com valores especiais em valor_bruto."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", "8331", "8331", "8331"],
            "variavel_nome": ["Área", "Área", "Área", "Área"],
            "variavel_unidade": ["Hectares", "Hectares", "Hectares", "Hectares"],
            "classificacao_id": ["782", "782", "782", "782"],
            "classificacao_nome": ["Produto", "Produto", "Produto", "Produto"],
            "categoria_codigo": ["40124", "40124", "40124", "40124"],
            "categoria_nome": ["Soja", "Soja", "Soja", "Soja"],
            "localidade_id": ["5103403", "5103403", "5103403", "5103403"],
            "localidade_nome": ["Cuiabá", "Cuiabá", "Cuiabá", "Cuiabá"],
            "nivel_territorial_id": ["N6", "N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município", "Município"],
            "periodo": ["2023", "2023", "2023", "2023"],
            "valor_bruto": ["790", "-", "..", "..."],
            "valor_numerico": [790.0, None, None, None],
        }
    )


@pytest.fixture()
def df_com_duplicatas() -> pd.DataFrame:
    """DataFrame com registros duplicados pela chave lógica."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", "8331"],
            "variavel_nome": ["Área", "Área"],
            "variavel_unidade": ["Hectares", "Hectares"],
            "classificacao_id": ["782", "782"],
            "classificacao_nome": ["Produto", "Produto"],
            "categoria_codigo": ["40124", "40124"],
            "categoria_nome": ["Soja", "Soja"],
            "localidade_id": ["5103403", "5103403"],
            "localidade_nome": ["Cuiabá", "Cuiabá"],
            "nivel_territorial_id": ["N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município"],
            "periodo": ["2023", "2023"],
            "valor_bruto": ["790", "800"],
            "valor_numerico": [790.0, 800.0],
        }
    )


@pytest.fixture()
def df_vazio() -> pd.DataFrame:
    """DataFrame vazio com as colunas corretas."""
    return pd.DataFrame(columns=COLUNAS_ORDEM)


# ---------------------------------------------------------------------------
# Testes: verificar_schema
# ---------------------------------------------------------------------------


class TestVerificarSchema:
    """Testes para verificação de schema."""

    def test_dataframe_valido(self, df_valido: pd.DataFrame) -> None:
        resultado = verificar_schema(df_valido)
        assert isinstance(resultado, ResultadoSchema)
        assert resultado.valido is True
        assert resultado.colunas_ausentes == []
        assert resultado.colunas_extras == []

    def test_coluna_ausente(self, df_valido: pd.DataFrame) -> None:
        df = df_valido.drop(columns=["periodo"])
        resultado = verificar_schema(df)
        assert resultado.valido is False
        assert "periodo" in resultado.colunas_ausentes

    def test_coluna_extra(self, df_valido: pd.DataFrame) -> None:
        df = df_valido.copy()
        df["coluna_inexistente"] = "valor"
        resultado = verificar_schema(df)
        assert resultado.valido is False
        assert "coluna_inexistente" in resultado.colunas_extras

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        resultado = verificar_schema(df_vazio)
        assert resultado.valido is True

    def test_multiplas_colunas_ausentes(self, df_valido: pd.DataFrame) -> None:
        df = df_valido.drop(columns=["periodo", "valor_bruto"])
        resultado = verificar_schema(df)
        assert resultado.valido is False
        assert len(resultado.colunas_ausentes) == 2


# ---------------------------------------------------------------------------
# Testes: verificar_nulos
# ---------------------------------------------------------------------------


class TestVerificarNulos:
    """Testes para verificação de valores nulos."""

    def test_dataframe_valido(self, df_valido: pd.DataFrame) -> None:
        resultado = verificar_nulos(df_valido)
        assert isinstance(resultado, ResultadoNulos)
        assert resultado.valido is True
        assert resultado.total_nulos == 0

    def test_nulos_presentes(self, df_com_nulos: pd.DataFrame) -> None:
        resultado = verificar_nulos(df_com_nulos)
        assert resultado.valido is False
        assert resultado.total_nulos > 0
        assert resultado.nulos_por_coluna["variavel_id"] == 1
        assert resultado.nulos_por_coluna["variavel_nome"] == 1
        assert resultado.nulos_por_coluna["categoria_codigo"] == 1

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        resultado = verificar_nulos(df_vazio)
        assert resultado.valido is True
        assert resultado.total_nulos == 0

    def test_colunas_obrigatorias_presentes(self) -> None:
        df = pd.DataFrame(
            {col: ["a"] for col in COLUNAS_ORDEM}
        )
        resultado = verificar_nulos(df)
        assert resultado.valido is True


# ---------------------------------------------------------------------------
# Testes: contar_valores_numericos
# ---------------------------------------------------------------------------


class TestContarValoresNumericos:
    """Testes para contagem de valores numéricos."""

    def test_todos_com_valor(self, df_valido: pd.DataFrame) -> None:
        resultado = contar_valores_numericos(df_valido)
        assert isinstance(resultado, ResultadoValoresNumericos)
        assert resultado.total_registros == 3
        assert resultado.com_valor == 3
        assert resultado.sem_valor == 0

    def test_alguns_sem_valor(self, df_com_especiais: pd.DataFrame) -> None:
        resultado = contar_valores_numericos(df_com_especiais)
        assert resultado.total_registros == 4
        assert resultado.com_valor == 1
        assert resultado.sem_valor == 3

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        resultado = contar_valores_numericos(df_vazio)
        assert resultado.total_registros == 0
        assert resultado.com_valor == 0
        assert resultado.sem_valor == 0

    def test_coluna_ausente(self) -> None:
        df = pd.DataFrame({"col": ["a"]})
        resultado = contar_valores_numericos(df)
        assert resultado.total_registros == 1
        assert resultado.com_valor == 0
        assert resultado.sem_valor == 1


# ---------------------------------------------------------------------------
# Testes: contar_valores_especiais
# ---------------------------------------------------------------------------


class TestContarValoresEspeciais:
    """Testes para contagem de valores especiais."""

    def test_todos_os_especiais(self, df_com_especiais: pd.DataFrame) -> None:
        resultado = contar_valores_especiais(df_com_especiais)
        assert isinstance(resultado, ResultadoValoresEspeciais)
        assert resultado.contagem["-"] == 1
        assert resultado.contagem[".."] == 1
        assert resultado.contagem["..."] == 1
        assert resultado.total == 3

    def test_apenas_menos(self) -> None:
        df = pd.DataFrame(
            {"valor_bruto": ["790", "-", "350"]},
        )
        resultado = contar_valores_especiais(df)
        assert resultado.contagem == {"-": 1}
        assert resultado.total == 1

    def test_nenhum_especial(self, df_valido: pd.DataFrame) -> None:
        resultado = contar_valores_especiais(df_valido)
        assert resultado.contagem == {}
        assert resultado.total == 0

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        resultado = contar_valores_especiais(df_vazio)
        assert resultado.contagem == {}
        assert resultado.total == 0

    def test_coluna_ausente(self) -> None:
        df = pd.DataFrame({"col": ["a"]})
        resultado = contar_valores_especiais(df)
        assert resultado.total == 0


# ---------------------------------------------------------------------------
# Testes: verificar_duplicidade
# ---------------------------------------------------------------------------


class TestVerificarDuplicidade:
    """Testes para verificação de duplicidade."""

    def test_sem_duplicatas(self, df_valido: pd.DataFrame) -> None:
        resultado = verificar_duplicidade(df_valido)
        assert isinstance(resultado, ResultadoDuplicidade)
        assert resultado.valido is True
        assert resultado.duplicatas == 0
        assert resultado.linhas_unicas == 3

    def test_com_duplicatas(self, df_com_duplicatas: pd.DataFrame) -> None:
        resultado = verificar_duplicidade(df_com_duplicatas)
        assert resultado.valido is False
        assert resultado.duplicatas == 1
        assert resultado.linhas_unicas == 1

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        resultado = verificar_duplicidade(df_vazio)
        assert resultado.valido is True
        assert resultado.duplicatas == 0

    def test_chave_logica_definida(self) -> None:
        assert CHAVE_LOGICA == [
            "variavel_id",
            "classificacao_id",
            "categoria_codigo",
            "localidade_id",
            "periodo",
        ]

    def test_chave_logica_nao_inclui_valores(self) -> None:
        assert "valor_bruto" not in CHAVE_LOGICA
        assert "valor_numerico" not in CHAVE_LOGICA

    def test_chave_logica_nao_inclui_nomes(self) -> None:
        assert "variavel_nome" not in CHAVE_LOGICA
        assert "localidade_nome" not in CHAVE_LOGICA
        assert "categoria_nome" not in CHAVE_LOGICA
        assert "classificacao_nome" not in CHAVE_LOGICA


# ---------------------------------------------------------------------------
# Testes: gerar_perfil
# ---------------------------------------------------------------------------


class TestGerarPerfil:
    """Testes para geração de perfil do dataset."""

    def test_perfil_basico(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert isinstance(perfil, ResultadoPerfil)
        assert perfil.num_linhas == 3
        assert perfil.num_colunas == 14

    def test_variaveis(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert "Área plantada" in perfil.variaveis
        assert "Quantidade produzida" in perfil.variaveis

    def test_produtos(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert "Soja" in perfil.produtos
        assert "Milho" in perfil.produtos

    def test_localidades(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert "Cuiabá (MT)" in perfil.localidades

    def test_periodos(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert "2023" in perfil.periodos

    def test_unidades(self, df_valido: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_valido)
        assert "Hectares" in perfil.unidades
        assert "Toneladas" in perfil.unidades

    def test_nulos(self, df_com_nulos: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_com_nulos)
        assert perfil.nulos_por_coluna["variavel_id"] == 1

    def test_duplicatas(self, df_com_duplicatas: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_com_duplicatas)
        assert perfil.duplicatas == 1

    def test_dataframe_vazio(self, df_vazio: pd.DataFrame) -> None:
        perfil = gerar_perfil(df_vazio)
        assert perfil.num_linhas == 0
        assert perfil.num_colunas == 14
        assert perfil.variaveis == []
        assert perfil.produtos == []
        assert perfil.localidades == []
        assert perfil.periodos == []
        assert perfil.duplicatas == 0


# ---------------------------------------------------------------------------
# Testes: dataset vazio
# ---------------------------------------------------------------------------


class TestDatasetVazio:
    """Testes para comportamento com dataset vazio."""

    def test_todas_funcoes_tratam_vazio(self, df_vazio: pd.DataFrame) -> None:
        schema = verificar_schema(df_vazio)
        assert schema.valido is True

        nulos = verificar_nulos(df_vazio)
        assert nulos.valido is True

        num = contar_valores_numericos(df_vazio)
        assert num.total_registros == 0

        esp = contar_valores_especiais(df_vazio)
        assert esp.total == 0

        dup = verificar_duplicidade(df_vazio)
        assert dup.valido is True

        perfil = gerar_perfil(df_vazio)
        assert perfil.num_linhas == 0
