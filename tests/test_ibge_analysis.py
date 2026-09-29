"""Testes para o módulo de análise exploratória do IBGE."""

from __future__ import annotations

import pandas as pd
import pytest

from agrodata.pipelines.ibge.analysis import (
    ResumoGeral,
    calcular_estatisticas,
    contar_municipios_por_produto_variavel,
    listar_produtos,
    listar_variaveis,
    ranking_municipios,
    resumir_dataset,
    verificar_duplicidades,
    verificar_unidades,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def df_valido() -> pd.DataFrame:
    """DataFrame válido com dados de teste."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", "8331", "8331", "8331", "214", "214"],
            "variavel_nome": [
                "Área plantada",
                "Área plantada",
                "Área plantada",
                "Área plantada",
                "Quantidade produzida",
                "Quantidade produzida",
            ],
            "variavel_unidade": ["Hectares", "Hectares", "Hectares", "Hectares", "Toneladas", "Toneladas"],
            "classificacao_id": ["782", "782", "782", "782", "782", "782"],
            "classificacao_nome": ["Produto", "Produto", "Produto", "Produto", "Produto", "Produto"],
            "categoria_codigo": ["40124", "40124", "40122", "40122", "40124", "40124"],
            "categoria_nome": ["Soja", "Soja", "Milho", "Milho", "Soja", "Soja"],
            "localidade_id": ["3100104", "3100203", "3100104", "3100203", "3100104", "3100203"],
            "localidade_nome": ["Município A", "Município B", "Município A", "Município B", "Município A", "Município B"],
            "nivel_territorial_id": ["N6", "N6", "N6", "N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município", "Município", "Município", "Município"],
            "periodo": ["2023", "2023", "2023", "2023", "2023", "2023"],
            "valor_bruto": ["1000", "2000", "500", "-", "50000", "30000"],
            "valor_numerico": [1000.0, 2000.0, 500.0, None, 50000.0, 30000.0],
        }
    )


@pytest.fixture()
def df_com_especiais() -> pd.DataFrame:
    """DataFrame com valores especiais."""
    return pd.DataFrame(
        {
            "variavel_id": ["8331", "8331", "8331", "8331"],
            "variavel_nome": ["Área", "Área", "Área", "Área"],
            "variavel_unidade": ["Hectares", "Hectares", "Hectares", "Hectares"],
            "classificacao_id": ["782", "782", "782", "782"],
            "classificacao_nome": ["Produto", "Produto", "Produto", "Produto"],
            "categoria_codigo": ["40124", "40124", "40124", "40124"],
            "categoria_nome": ["Soja", "Soja", "Soja", "Soja"],
            "localidade_id": ["3100104", "3100203", "3100302", "3100401"],
            "localidade_nome": ["Município A", "Município B", "Município C", "Município D"],
            "nivel_territorial_id": ["N6", "N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município", "Município"],
            "periodo": ["2023", "2023", "2023", "2023"],
            "valor_bruto": ["1000", "-", "..", "..."],
            "valor_numerico": [1000.0, None, None, None],
        }
    )


@pytest.fixture()
def df_vazio() -> pd.DataFrame:
    """DataFrame vazio."""
    return pd.DataFrame(
        columns=[
            "variavel_id", "variavel_nome", "variavel_unidade",
            "classificacao_id", "classificacao_nome",
            "categoria_codigo", "categoria_nome",
            "localidade_id", "localidade_nome",
            "nivel_territorial_id", "nivel_territorial_nome",
            "periodo", "valor_bruto", "valor_numerico",
        ]
    )


# ---------------------------------------------------------------------------
# Testes: listar_variaveis
# ---------------------------------------------------------------------------


class TestListarVariaveis:
    """Testes para listagem de variáveis."""

    def test_lista_variaveis_unicas(self, df_valido: pd.DataFrame) -> None:
        variaveis = listar_variaveis(df_valido)
        assert len(variaveis) == 2
        ids = {v["id"] for v in variaveis}
        assert ids == {"8331", "214"}

    def test_campos_completos(self, df_valido: pd.DataFrame) -> None:
        variaveis = listar_variaveis(df_valido)
        for v in variaveis:
            assert "id" in v
            assert "nome" in v
            assert "unidade" in v

    def test_dataset_vazio(self, df_vazio: pd.DataFrame) -> None:
        variaveis = listar_variaveis(df_vazio)
        assert variaveis == []


# ---------------------------------------------------------------------------
# Testes: listar_produtos
# ---------------------------------------------------------------------------


class TestListarProdutos:
    """Testes para listagem de produtos."""

    def test_lista_produtos_unicos(self, df_valido: pd.DataFrame) -> None:
        produtos = listar_produtos(df_valido)
        assert len(produtos) == 2
        codigos = {p["codigo"] for p in produtos}
        assert codigos == {"40124", "40122"}

    def test_dataset_vazio(self, df_vazio: pd.DataFrame) -> None:
        produtos = listar_produtos(df_vazio)
        assert produtos == []


# ---------------------------------------------------------------------------
# Testes: contar_municipios_por_produto_variavel
# ---------------------------------------------------------------------------


class TestContarMunicipios:
    """Testes para contagem de municípios por produto × variável."""

    def test_contagem_correta(self, df_valido: pd.DataFrame) -> None:
        contagem = contar_municipios_por_produto_variavel(df_valido)
        assert len(contagem) == 3  # 8331/40124, 8331/40122, 214/40124

    def test_so_com_valores_validos(self, df_com_especiais: pd.DataFrame) -> None:
        contagem = contar_municipios_por_produto_variavel(df_com_especiais)
        # Apenas 1 registro válido (1000)
        assert contagem["num_municipios_com_dados"].sum() == 1


# ---------------------------------------------------------------------------
# Testes: calcular_estatisticas
# ---------------------------------------------------------------------------


class TestCalcularEstatisticas:
    """Testes para cálculo de estatísticas."""

    def test_estatisticas_basicas(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido)
        assert len(stats) == 3  # 3 combinações

    def test_exclusao_valores_nulos(self, df_com_especiais: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_com_especiais)
        assert len(stats) == 1
        assert stats[0].registros_validos == 1
        assert stats[0].registros_ausentes == 3

    def test_minimo(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, variavel_id="8331", categoria_codigo="40124")
        assert len(stats) == 1
        assert stats[0].minimo == 1000.0

    def test_maximo(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, variavel_id="8331", categoria_codigo="40124")
        assert len(stats) == 1
        assert stats[0].maximo == 2000.0

    def test_media(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, variavel_id="8331", categoria_codigo="40124")
        assert len(stats) == 1
        assert stats[0].media == 1500.0

    def test_mediana(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, variavel_id="8331", categoria_codigo="40124")
        assert len(stats) == 1
        assert stats[0].mediana == 1500.0

    def test_filtro_por_variavel(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, variavel_id="8331")
        assert len(stats) == 2  # 40124 e 40122

    def test_filtro_por_produto(self, df_valido: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_valido, categoria_codigo="40124")
        assert len(stats) == 2  # 8331 e 214

    def test_dataset_vazio(self, df_vazio: pd.DataFrame) -> None:
        stats = calcular_estatisticas(df_vazio)
        assert stats == []


# ---------------------------------------------------------------------------
# Testes: ranking_municipios
# ---------------------------------------------------------------------------


class TestRankingMunicipios:
    """Testes para ranking de municípios."""

    def test_ranking_maiores(self, df_valido: pd.DataFrame) -> None:
        ranking = ranking_municipios(df_valido, "8331", "40124", n=2)
        assert len(ranking.maiores) == 2
        assert ranking.maiores[0].valor_numerico == 2000.0
        assert ranking.maiores[1].valor_numerico == 1000.0

    def test_ranking_menores(self, df_valido: pd.DataFrame) -> None:
        ranking = ranking_municipios(df_valido, "8331", "40124", n=2)
        assert len(ranking.menores) == 2
        assert ranking.menores[0].valor_numerico == 1000.0
        assert ranking.menores[1].valor_numerico == 2000.0

    def test_exclusao_valores_especiais(self, df_com_especiais: pd.DataFrame) -> None:
        ranking = ranking_municipios(df_com_especiais, "8331", "40124", n=10)
        assert len(ranking.maiores) == 1
        assert ranking.maiores[0].valor_numerico == 1000.0

    def test_ranking_vazio(self, df_vazio: pd.DataFrame) -> None:
        ranking = ranking_municipios(df_vazio, "8331", "40124")
        assert ranking.maiores == []
        assert ranking.menores == []


# ---------------------------------------------------------------------------
# Testes: verificar_unidades
# ---------------------------------------------------------------------------


class TestVerificarUnidades:
    """Testes para verificação de unidades."""

    def test_unidade_consistente(self, df_valido: pd.DataFrame) -> None:
        unidades = verificar_unidades(df_valido)
        assert len(unidades) == 2
        for u in unidades:
            assert u.consistente is True
            assert len(u.unidades_encontradas) == 1

    def test_unidade_inconsistente(self) -> None:
        df = pd.DataFrame(
            {
                "variavel_id": ["8331", "8331"],
                "variavel_nome": ["Área", "Área"],
                "variavel_unidade": ["Hectares", "Alqueires"],
                "classificacao_id": ["782", "782"],
                "classificacao_nome": ["Produto", "Produto"],
                "categoria_codigo": ["40124", "40124"],
                "categoria_nome": ["Soja", "Soja"],
                "localidade_id": ["3100104", "3100203"],
                "localidade_nome": ["A", "B"],
                "nivel_territorial_id": ["N6", "N6"],
                "nivel_territorial_nome": ["Município", "Município"],
                "periodo": ["2023", "2023"],
                "valor_bruto": ["1000", "2000"],
                "valor_numerico": [1000.0, 2000.0],
            }
        )
        unidades = verificar_unidades(df)
        assert len(unidades) == 1
        assert unidades[0].consistente is False
        assert len(unidades[0].unidades_encontradas) == 2


# ---------------------------------------------------------------------------
# Testes: verificar_duplicidades
# ---------------------------------------------------------------------------


class TestVerificarDuplicidades:
    """Testes para verificação de duplicidades."""

    def test_sem_duplicatas(self, df_valido: pd.DataFrame) -> None:
        duplicatas = verificar_duplicidades(df_valido)
        assert duplicatas == 0

    def test_com_duplicatas(self) -> None:
        df = pd.DataFrame(
            {
                "variavel_id": ["8331", "8331"],
                "variavel_nome": ["Área", "Área"],
                "variavel_unidade": ["Hectares", "Hectares"],
                "classificacao_id": ["782", "782"],
                "classificacao_nome": ["Produto", "Produto"],
                "categoria_codigo": ["40124", "40124"],
                "categoria_nome": ["Soja", "Soja"],
                "localidade_id": ["3100104", "3100104"],
                "localidade_nome": ["A", "A"],
                "nivel_territorial_id": ["N6", "N6"],
                "nivel_territorial_nome": ["Município", "Município"],
                "periodo": ["2023", "2023"],
                "valor_bruto": ["1000", "2000"],
                "valor_numerico": [1000.0, 2000.0],
            }
        )
        duplicatas = verificar_duplicidades(df)
        assert duplicatas == 1

    def test_dataset_vazio(self, df_vazio: pd.DataFrame) -> None:
        duplicatas = verificar_duplicidades(df_vazio)
        assert duplicatas == 0


# ---------------------------------------------------------------------------
# Testes: resumir_dataset
# ---------------------------------------------------------------------------


class TestResumirDataset:
    """Testes para resumo geral do dataset."""

    def test_resumo_basico(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert isinstance(resumo, ResumoGeral)
        assert resumo.num_linhas == 6
        assert resumo.num_colunas == 14
        assert resumo.num_municipios == 2

    def test_resumo_variaveis(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert len(resumo.variaveis) == 2

    def test_resumo_produtos(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert len(resumo.produtos) == 2

    def test_resumo_estatisticas(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert len(resumo.estatisticas) == 3

    def test_resumo_rankings(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert len(resumo.rankings) == 3

    def test_resumo_duplicidades(self, df_valido: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_valido)
        assert resumo.duplicidades == 0

    def test_dataset_vazio(self, df_vazio: pd.DataFrame) -> None:
        resumo = resumir_dataset(df_vazio)
        assert resumo.num_linhas == 0
        assert resumo.num_municipios == 0
        assert resumo.estatisticas == []
        assert resumo.rankings == []
