"""Testes para o módulo de camada analítica do IBGE."""

from __future__ import annotations

import pandas as pd
import pytest

from agrodata.pipelines.ibge.analytics import (
    COLUNAS_ANALITICAS,
    MAPEAMENTO_VARIAVEIS,
    contar_ausentes,
    transformar_long_para_wide,
    verificar_unicidade,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def df_long_completo() -> pd.DataFrame:
    """DataFrame long com 2 municipios, 2 produtos, 4 variaveis."""
    dados = []
    municipios = [
        ("3100104", "Municipio A", "N6", "Municipio"),
        ("3100203", "Municipio B", "N6", "Municipio"),
    ]
    produtos = [("40124", "Soja"), ("40122", "Milho")]
    variaveis = [
        ("8331", "Area plantada", "Hectares"),
        ("214", "Quantidade produzida", "Toneladas"),
        ("112", "Rendimento medio", "Quilogramas por Hectare"),
        ("215", "Valor da producao", "Mil Reais"),
    ]

    for mid, mnome, nid, nnome in municipios:
        for pcod, pnome in produtos:
            for vid, vnome, vunid in variaveis:
                dados.append({
                    "variavel_id": vid,
                    "variavel_nome": vnome,
                    "variavel_unidade": vunid,
                    "classificacao_id": "782",
                    "classificacao_nome": "Produto",
                    "categoria_codigo": pcod,
                    "categoria_nome": pnome,
                    "localidade_id": mid,
                    "localidade_nome": mnome,
                    "nivel_territorial_id": nid,
                    "nivel_territorial_nome": nnome,
                    "periodo": "2023",
                    "valor_bruto": "1000",
                    "valor_numerico": 1000.0,
                })

    return pd.DataFrame(dados)


@pytest.fixture()
def df_long_com_ausentes() -> pd.DataFrame:
    """DataFrame long com valores ausentes em algumas variaveis."""
    dados = [
        {
            "variavel_id": "8331", "variavel_nome": "Area", "variavel_unidade": "Hectares",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100104", "localidade_nome": "Municipio A",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "1000", "valor_numerico": 1000.0,
        },
        {
            "variavel_id": "214", "variavel_nome": "Producao", "variavel_unidade": "Toneladas",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100104", "localidade_nome": "Municipio A",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "500", "valor_numerico": 500.0,
        },
        {
            "variavel_id": "112", "variavel_nome": "Rendimento", "variavel_unidade": "kg/ha",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100104", "localidade_nome": "Municipio A",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "3500", "valor_numerico": 3500.0,
        },
        {
            "variavel_id": "215", "variavel_nome": "Valor", "variavel_unidade": "Mil Reais",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100104", "localidade_nome": "Municipio A",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "2000", "valor_numerico": 2000.0,
        },
        {
            "variavel_id": "8331", "variavel_nome": "Area", "variavel_unidade": "Hectares",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100203", "localidade_nome": "Municipio B",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "500", "valor_numerico": 500.0,
        },
        {
            "variavel_id": "214", "variavel_nome": "Producao", "variavel_unidade": "Toneladas",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100203", "localidade_nome": "Municipio B",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "-", "valor_numerico": None,
        },
        {
            "variavel_id": "112", "variavel_nome": "Rendimento", "variavel_unidade": "kg/ha",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100203", "localidade_nome": "Municipio B",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "-", "valor_numerico": None,
        },
        {
            "variavel_id": "215", "variavel_nome": "Valor", "variavel_unidade": "Mil Reais",
            "classificacao_id": "782", "classificacao_nome": "Produto",
            "categoria_codigo": "40124", "categoria_nome": "Soja",
            "localidade_id": "3100203", "localidade_nome": "Municipio B",
            "nivel_territorial_id": "N6", "nivel_territorial_nome": "Municipio",
            "periodo": "2023", "valor_bruto": "-", "valor_numerico": None,
        },
    ]
    return pd.DataFrame(dados)


@pytest.fixture()
def df_long_vazio() -> pd.DataFrame:
    """DataFrame long vazio."""
    return pd.DataFrame(columns=[
        "variavel_id", "variavel_nome", "variavel_unidade",
        "classificacao_id", "classificacao_nome",
        "categoria_codigo", "categoria_nome",
        "localidade_id", "localidade_nome",
        "nivel_territorial_id", "nivel_territorial_nome",
        "periodo", "valor_bruto", "valor_numerico",
    ])


@pytest.fixture()
def df_long_variavel_ausente() -> pd.DataFrame:
    """DataFrame long sem a variavel 112 (rendimento)."""
    dados = []
    for vid in ["8331", "214", "215"]:
        dados.append({
            "variavel_id": vid,
            "variavel_nome": f"Variavel {vid}",
            "variavel_unidade": "Unidade",
            "classificacao_id": "782",
            "classificacao_nome": "Produto",
            "categoria_codigo": "40124",
            "categoria_nome": "Soja",
            "localidade_id": "3100104",
            "localidade_nome": "Municipio A",
            "nivel_territorial_id": "N6",
            "nivel_territorial_nome": "Municipio",
            "periodo": "2023",
            "valor_bruto": "1000",
            "valor_numerico": 1000.0,
        })
    return pd.DataFrame(dados)


# ---------------------------------------------------------------------------
# Testes: transformar_long_para_wide
# ---------------------------------------------------------------------------


class TestTransformarLongParaWide:
    """Testes para transformacao de long para wide."""

    def test_retorna_dataframe(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert isinstance(df_wide, pd.DataFrame)

    def test_numero_colunas(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert df_wide.shape[1] == 11

    def test_colunas_esperadas(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert list(df_wide.columns) == COLUNAS_ANALITICAS

    def test_numero_linhas(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        # 2 municipios x 2 produtos = 4 linhas
        assert df_wide.shape[0] == 4

    def test_preserva_municipios(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        municipios = sorted(df_wide["municipio_id"].unique().tolist())
        assert municipios == ["3100104", "3100203"]

    def test_preserva_produtos(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        produtos = sorted(df_wide["produto_codigo"].unique().tolist())
        assert produtos == ["40122", "40124"]

    def test_preserva_periodo(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert all(df_wide["periodo"] == "2023")

    def test_coluna_area_plantada(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert "area_plantada_ha" in df_wide.columns
        assert df_wide["area_plantada_ha"].notna().all()

    def test_coluna_quantidade_produzida(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert "quantidade_produzida_t" in df_wide.columns

    def test_coluna_rendimento_medio(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert "rendimento_medio_kg_ha" in df_wide.columns

    def test_coluna_valor_producao(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert "valor_producao_mil_reais" in df_wide.columns


# ---------------------------------------------------------------------------
# Testes: valores ausentes
# ---------------------------------------------------------------------------


class TestValoresAusentes:
    """Testes para preservacao de valores ausentes."""

    def test_ausentes_preservados(self, df_long_com_ausentes: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_com_ausentes)
        mb = df_wide[df_wide["municipio_id"] == "3100203"].iloc[0]
        assert mb["area_plantada_ha"] == 500.0
        assert pd.isna(mb["quantidade_produzida_t"])
        assert pd.isna(mb["rendimento_medio_kg_ha"])
        assert pd.isna(mb["valor_producao_mil_reais"])

    def test_nao_transforma_ausente_em_zero(self, df_long_com_ausentes: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_com_ausentes)
        mb = df_wide[df_wide["municipio_id"] == "3100203"].iloc[0]
        assert mb["quantidade_produzida_t"] != 0.0
        assert pd.isna(mb["quantidade_produzida_t"])

    def test_contar_ausentes(self, df_long_com_ausentes: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_com_ausentes)
        ausentes = contar_ausentes(df_wide)
        assert ausentes["area_plantada_ha"] == 0
        assert ausentes["quantidade_produzida_t"] == 1
        assert ausentes["rendimento_medio_kg_ha"] == 1
        assert ausentes["valor_producao_mil_reais"] == 1


# ---------------------------------------------------------------------------
# Testes: preservacao de tipos
# ---------------------------------------------------------------------------


class TestPreservacaoTipos:
    """Testes para preservacao de tipos."""

    def test_ids_sao_string(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert str(df_wide["municipio_id"].dtype) == "string"
        assert str(df_wide["produto_codigo"].dtype) == "string"
        assert str(df_wide["periodo"].dtype) == "string"

    def test_periodo_e_string(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        assert all(isinstance(p, str) for p in df_wide["periodo"])


# ---------------------------------------------------------------------------
# Testes: unicidade
# ---------------------------------------------------------------------------


class TestUnicidade:
    """Testes para verificacao de unicidade."""

    def test_chave_unica(self, df_long_completo: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_completo)
        eh_unico, duplicatas = verificar_unicidade(df_wide)
        assert eh_unico is True
        assert duplicatas == 0

    def test_dataset_vazio(self, df_long_vazio: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_vazio)
        eh_unico, duplicatas = verificar_unicidade(df_wide)
        assert eh_unico is True
        assert duplicatas == 0


# ---------------------------------------------------------------------------
# Testes: dataset vazio
# ---------------------------------------------------------------------------


class TestDatasetVazio:
    """Testes para comportamento com dataset vazio."""

    def test_transformacao_vazia(self, df_long_vazio: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_vazio)
        assert len(df_wide) == 0
        assert list(df_wide.columns) == COLUNAS_ANALITICAS

    def test_ausentes_vazio(self, df_long_vazio: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_vazio)
        ausentes = contar_ausentes(df_wide)
        assert all(v == 0 for v in ausentes.values())


# ---------------------------------------------------------------------------
# Testes: variavel ausente
# ---------------------------------------------------------------------------


class TestVariavelAusente:
    """Testes para quando uma variavel esperada nao esta presente."""

    def test_variavel_112_ausente(self, df_long_variavel_ausente: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_variavel_ausente)
        assert "rendimento_medio_kg_ha" in df_wide.columns
        assert df_wide["rendimento_medio_kg_ha"].isna().all()

    def test_outras_variaveis_presentes(self, df_long_variavel_ausente: pd.DataFrame) -> None:
        df_wide = transformar_long_para_wide(df_long_variavel_ausente)
        assert df_wide["area_plantada_ha"].notna().all()
        assert df_wide["quantidade_produzida_t"].notna().all()
        assert df_wide["valor_producao_mil_reais"].notna().all()


# ---------------------------------------------------------------------------
# Testes: combinacoes com todos os valores ausentes
# ---------------------------------------------------------------------------


class TestCombinacaoTodosAusentes:
    """Testes para combinacoes onde TODOS os valores sao ausentes.

    Regressao: pivot_table(dropna=True) descarta linhas onde todos os valores
    sao NaN. Combinacoes com todos os valores '-' no long devem ser excluidas
    do wide, nao preenchidas com zero.
    """

    def test_combinacao_ausente_excluida(self) -> None:
        """Combinacao com todos os 4 valores ausentes nao aparece no wide."""
        dados = [
            # Municipio A + Soja: todos presentes
            *[
                {
                    "variavel_id": vid, "variavel_nome": f"V{vid}",
                    "variavel_unidade": "U", "classificacao_id": "782",
                    "classificacao_nome": "Produto", "categoria_codigo": "40124",
                    "categoria_nome": "Soja", "localidade_id": "3100104",
                    "localidade_nome": "Mun A", "nivel_territorial_id": "N6",
                    "nivel_territorial_nome": "Municipio", "periodo": "2023",
                    "valor_bruto": "1000", "valor_numerico": 1000.0,
                }
                for vid in ["8331", "214", "112", "215"]
            ],
            # Municipio B + Soja: todos ausentes
            *[
                {
                    "variavel_id": vid, "variavel_nome": f"V{vid}",
                    "variavel_unidade": "U", "classificacao_id": "782",
                    "classificacao_nome": "Produto", "categoria_codigo": "40124",
                    "categoria_nome": "Soja", "localidade_id": "3100203",
                    "localidade_nome": "Mun B", "nivel_territorial_id": "N6",
                    "nivel_territorial_nome": "Municipio", "periodo": "2023",
                    "valor_bruto": "-", "valor_numerico": None,
                }
                for vid in ["8331", "214", "112", "215"]
            ],
        ]
        df_long = pd.DataFrame(dados)
        df_wide = transformar_long_para_wide(df_long)

        # Apenas Municipio A + Soja deve estar no wide
        assert len(df_wide) == 1
        assert df_wide.iloc[0]["municipio_id"] == "3100104"

    def test_ausente_nao_vira_zero(self) -> None:
        """Valores ausentes nao sao convertidos para zero."""
        dados = [
            {
                "variavel_id": "8331", "variavel_nome": "Area",
                "variavel_unidade": "Hectares", "classificacao_id": "782",
                "classificacao_nome": "Produto", "categoria_codigo": "40124",
                "categoria_nome": "Soja", "localidade_id": "3100104",
                "localidade_nome": "Mun A", "nivel_territorial_id": "N6",
                "nivel_territorial_nome": "Municipio", "periodo": "2023",
                "valor_bruto": "1000", "valor_numerico": 1000.0,
            },
            {
                "variavel_id": "214", "variavel_nome": "Producao",
                "variavel_unidade": "Toneladas", "classificacao_id": "782",
                "classificacao_nome": "Produto", "categoria_codigo": "40124",
                "categoria_nome": "Soja", "localidade_id": "3100104",
                "localidade_nome": "Mun A", "nivel_territorial_id": "N6",
                "nivel_territorial_nome": "Municipio", "periodo": "2023",
                "valor_bruto": "-", "valor_numerico": None,
            },
        ]
        df_long = pd.DataFrame(dados)
        df_wide = transformar_long_para_wide(df_long)

        assert df_wide.iloc[0]["area_plantada_ha"] == 1000.0
        assert pd.isna(df_wide.iloc[0]["quantidade_produzida_t"])


# ---------------------------------------------------------------------------
# Testes: mapeamento
# ---------------------------------------------------------------------------


class TestMapeamento:
    """Testes para o mapeamento de variaveis."""

    def test_mapeamento_completo(self) -> None:
        assert "8331" in MAPEAMENTO_VARIAVEIS
        assert "214" in MAPEAMENTO_VARIAVEIS
        assert "112" in MAPEAMENTO_VARIAVEIS
        assert "215" in MAPEAMENTO_VARIAVEIS

    def test_nomes_com_unidade(self) -> None:
        assert "ha" in MAPEAMENTO_VARIAVEIS["8331"]
        assert "_t" in MAPEAMENTO_VARIAVEIS["214"]
        assert "kg_ha" in MAPEAMENTO_VARIAVEIS["112"]
        assert "mil_reais" in MAPEAMENTO_VARIAVEIS["215"]
