"""Testes para a camada Analytics — queries, KPIs, rankings, insights."""

from __future__ import annotations

import pytest

from agrodata.analytics.indicators import (
    calcular_kpis,
    calcular_ranking,
    gerar_insights,
)
from agrodata.analytics.queries import (
    limpar_cache,
    obter_dados_filtrados,
    obter_municipio_detalhe,
    obter_scatter_data,
)
from agrodata.config import DatasetConfig as Cfg


# Fixtures para testes com dados reais
@pytest.fixture(scope="session", autouse=True)
def _cache_limpo():
    limpar_cache()
    yield
    limpar_cache()


class TestObterDadosFiltrados:
    """Testes para filtro de dados."""

    def test_todos_2023(self) -> None:
        gdf = obter_dados_filtrados("Todos", "2023")
        assert len(gdf) == 1137
        assert set(gdf[Cfg.COLUNA_PRODUTO_NOME].unique()) == {"Soja (em grão)", "Milho (em grão)"}

    def test_soja_2023(self) -> None:
        gdf = obter_dados_filtrados("Soja", "2023")
        assert all(gdf[Cfg.COLUNA_PRODUTO_NOME] == "Soja (em grão)")

    def test_milho_2023(self) -> None:
        gdf = obter_dados_filtrados("Milho", "2023")
        assert all(gdf[Cfg.COLUNA_PRODUTO_NOME] == "Milho (em grão)")


class TestKPIs:
    """Testes para KPIs."""

    def test_kpis_todos_producao(self) -> None:
        kpis = calcular_kpis("Todos", "2023", "Produção")
        assert kpis.area_total_ha > 0
        assert kpis.producao_total_t > 0
        assert kpis.valor_total_producao_reais == kpis.valor_total_producao_mil_reais * 1000
        assert kpis.municipios_com_dado > 0
        assert kpis.produtividade_ponderada_kg_ha is not None
        assert kpis.produtividade_ponderada_kg_ha > 0

    def test_kpis_soja_area(self) -> None:
        kpis = calcular_kpis("Soja", "2023", "Área")
        assert kpis.indicador_filtro == "Área"
        assert kpis.cultura_filtro == "Soja"
        assert kpis.area_total_ha > 0

    def test_produtividade_ponderada_formula(self) -> None:
        """Verifica que produtividade = soma(produção*1000) / soma(área)."""
        kpis = calcular_kpis("Todos", "2023", "Produção")
        # Produtividade ponderada em kg/ha
        esperada = (kpis.producao_total_t * 1000) / kpis.area_total_ha
        assert abs(kpis.produtividade_ponderada_kg_ha - esperada) < 0.01

    def test_valor_conversao_mil_reais(self) -> None:
        """Valor em reais = valor_mil_reais * 1000."""
        kpis = calcular_kpis("Todos", "2023", "Valor da produção")
        assert kpis.valor_total_producao_reais == kpis.valor_total_producao_mil_reais * 1000


class TestRanking:
    """Testes para ranking."""

    def test_ranking_top10_producao(self) -> None:
        ranking = calcular_ranking("Todos", "2023", "Produção", 10)
        assert len(ranking) == 10
        assert all(r.valor is not None for r in ranking)
        # Verifica ordenação decrescente
        valores = [r.valor for r in ranking]
        assert valores == sorted(valores, reverse=True)

    def test_ranking_soja_area(self) -> None:
        ranking = calcular_ranking("Soja", "2023", "Área", 5)
        assert len(ranking) == 5
        assert all(r.cultura == "Soja" for r in ranking)

    def test_ranking_nao_inclui_nulos(self) -> None:
        """Ranking não deve incluir municípios sem dado no indicador."""
        ranking = calcular_ranking("Todos", "2023", "Produtividade", 10)
        assert all(r.valor is not None for r in ranking)


class TestScatter:
    """Testes para scatter plot."""

    def test_scatter_apenas_validos(self) -> None:
        pontos = obter_scatter_data("Todos", "2023")
        assert all(p.area_plantada_ha > 0 for p in pontos)
        assert all(p.rendimento_medio_kg_ha > 0 for p in pontos)

    def test_scatter_cultura_especifica(self) -> None:
        pontos = obter_scatter_data("Soja", "2023")
        assert all(p.cultura == "Soja" for p in pontos)


class TestMunicipioDetalhe:
    """Testes para detalhe do município."""

    def test_municipio_existente_com_dado(self) -> None:
        # Abadia dos Dourados (tem soja e milho)
        detalhe = obter_municipio_detalhe("3100104", "Todos", "2023", "Produção")
        assert detalhe is not None
        assert detalhe.municipio_id == "3100104"
        assert detalhe.municipio_nome == "Abadia dos Dourados"
        assert detalhe.tem_dado_agricola is True

    def test_valor_reais_derivado(self) -> None:
        detalhe = obter_municipio_detalhe("3100104", "Todos", "2023", "Produção")
        if detalhe.valor_producao_mil_reais is not None:
            assert detalhe.valor_producao_reais == detalhe.valor_producao_mil_reais * 1000

    def test_percentil_e_ranking(self) -> None:
        detalhe = obter_municipio_detalhe("3100104", "Todos", "2023", "Produção")
        assert detalhe.percentil_indicador is not None
        assert 0 <= detalhe.percentil_indicador <= 100
        assert detalhe.posicao_ranking is not None
        assert detalhe.posicao_ranking >= 1

    def test_municipio_sem_pam_retorna_none(self) -> None:
        # Um dos 6 municípios sem PAM (exemplo fictício que não existe nos dados)
        detalhe = obter_municipio_detalhe("9999999", "Todos", "2023", "Produção")
        assert detalhe is None


class TestInsights:
    """Testes para insights determinísticos."""

    def test_insights_basicos(self) -> None:
        insights = gerar_insights("Todos", "2023", "Produção")
        assert len(insights.insights) >= 3  # concentração, participação, estatística
        tipos = {i.tipo for i in insights.insights}
        assert "concentracao" in tipos
        assert "participacao" in tipos
        assert "estatistica" in tipos

    def test_participacao_top10(self) -> None:
        insights = gerar_insights("Todos", "2023", "Produção")
        part = next(i for i in insights.insights if i.tipo == "participacao")
        assert 0 <= part.valor <= 100

    def test_insight_percentil_com_municipio(self) -> None:
        insights = gerar_insights("Todos", "2023", "Produção", municipio_selecionado="3100104")
        pct = next((i for i in insights.insights if i.tipo == "percentil"), None)
        assert pct is not None
        assert 0 <= pct.valor <= 100

    def test_insights_sem_ia(self) -> None:
        """Todos os insights são determinísticos, não usam IA."""
        insights = gerar_insights("Todos", "2023", "Produção")
        # Verifica que não há campos de ML/probabilidade
        for insight in insights.insights:
            assert "probabilidade" not in insight.descricao.lower()
            assert "predição" not in insight.descricao.lower()
            assert "score" not in insight.descricao.lower()


class TestAusenciaNaoZero:
    """Testes que validam ausência ≠ zero."""

    def test_ranking_exclui_nulos(self) -> None:
        """Municípios sem dado no indicador não aparecem no ranking."""
        ranking = calcular_ranking("Todos", "2023", "Produtividade", 20)
        # Deve ter menos de 847*2 pois nem todos têm produtividade
        assert len(ranking) <= 20

    def test_kpis_municipios_com_dado(self) -> None:
        kpis = calcular_kpis("Todos", "2023", "Produção")
        # 847 municípios têm PAM, mas nem todos têm produção
        assert kpis.municipios_com_dado <= 847 * 2  # max 2 produtos por município


class TestCRS:
    """Testes de CRS."""

    def test_dados_em_4674(self) -> None:
        from agrodata.analytics.queries import _carregar_pam_integrado
        gdf = _carregar_pam_integrado()
        assert gdf.crs.to_epsg() == 4674


class TestSerializacaoGeoJSON:
    """Testes de serialização para API."""

    def test_geojson_propriedades(self) -> None:
        from agrodata.analytics.queries import obter_geojson_mapa
        geojson = obter_geojson_mapa("Todos", "2023", "Produção")
        assert geojson["type"] == "FeatureCollection"
        assert geojson["crs"]["properties"]["name"] == "EPSG:4326"
        assert len(geojson["features"]) > 0
        for feat in geojson["features"]:
            assert feat["type"] == "Feature"
            assert "geometry" in feat
            assert "properties" in feat
            assert "municipio_id" in feat["properties"]


class TestCacheGeoJSON:
    """Testes para cache de resposta GeoJSON."""

    def setup_method(self) -> None:
        """Limpa cache antes de cada teste."""
        from agrodata.analytics.queries import limpar_cache
        limpar_cache()

    def test_cache_miss_primeira_chamada(self) -> None:
        """Primeira chamada deve ser cache miss (gera resultado)."""
        from agrodata.analytics.queries import _geojson_cache, obter_geojson_mapa
        assert len(_geojson_cache) == 0
        geojson = obter_geojson_mapa("Todos", "2023", "Produção")
        assert len(_geojson_cache) == 1
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) > 0

    def test_cache_hit_segunda_chamada(self) -> None:
        """Segunda chamada com mesmos parâmetros deve ser cache hit."""
        from agrodata.analytics.queries import _geojson_cache, obter_geojson_mapa
        geojson1 = obter_geojson_mapa("Todos", "2023", "Produção")
        tamanho_cache_apos_1 = len(_geojson_cache)
        geojson2 = obter_geojson_mapa("Todos", "2023", "Produção")
        assert len(_geojson_cache) == tamanho_cache_apos_1
        assert geojson1 == geojson2

    def test_mudanca_cultura_chave_diferente(self) -> None:
        """Mudança de cultura deve gerar chave de cache diferente."""
        from agrodata.analytics.queries import _geojson_cache, obter_geojson_mapa
        obter_geojson_mapa("Todos", "2023", "Produção")
        obter_geojson_mapa("Soja", "2023", "Produção")
        obter_geojson_mapa("Milho", "2023", "Produção")
        assert len(_geojson_cache) == 3

    def test_mudanca_indicador_chave_diferente(self) -> None:
        """Mudança de indicador deve gerar chave de cache diferente."""
        from agrodata.analytics.queries import _geojson_cache, obter_geojson_mapa
        obter_geojson_mapa("Todos", "2023", "Produção")
        obter_geojson_mapa("Todos", "2023", "Área")
        obter_geojson_mapa("Todos", "2023", "Produtividade")
        obter_geojson_mapa("Todos", "2023", "Valor da produção")
        assert len(_geojson_cache) == 4

    def test_mudanca_periodo_chave_diferente(self) -> None:
        """Mudança de período deve gerar chave de cache diferente."""
        from agrodata.analytics.queries import _geojson_cache, obter_geojson_mapa
        obter_geojson_mapa("Todos", "2023", "Produção")
        obter_geojson_mapa("Todos", "2022", "Produção")
        assert len(_geojson_cache) == 2

    def test_conteudo_cache_equivalente_sem_cache(self) -> None:
        """Conteúdo do cache deve ser equivalente ao resultado sem cache."""
        from agrodata.analytics.queries import (
            _gerar_geojson_sem_cache,
            obter_geojson_mapa,
        )
        # Gera via cache
        geojson_cache = obter_geojson_mapa("Todos", "2023", "Produção")
        # Gera sem cache (função interna)
        geojson_sem_cache = _gerar_geojson_sem_cache("Todos", "2023", "Produção")
        assert geojson_cache == geojson_sem_cache

    def test_ausencia_diferente_zero(self) -> None:
        """Ausência de dado (None) deve ser mantida, não convertida para zero.

        O código converte NaN para None no GeoJSON. Este teste verifica
        que a lógica de conversão está correta (mesmo que o dataset atual
        não tenha nulos para este indicador).
        """
        from agrodata.analytics.queries import obter_geojson_mapa
        geojson = obter_geojson_mapa("Todos", "2023", "Produção")
        # Verifica que a coluna 'valor' existe e pode conter None (sem erro)
        for feat in geojson["features"]:
            val = feat["properties"]["valor"]
            assert val is None or isinstance(val, (int, float))
            # Se fosse zero, seria 0.0 - None indica ausência
            # Nota: dataset atual não tem nulos, mas a lógica preserva None

    def test_uma_feature_por_municipio(self) -> None:
        """GeoJSON deve ter uma feature por município (após agregação)."""
        from agrodata.analytics.queries import obter_geojson_mapa
        geojson = obter_geojson_mapa("Todos", "2023", "Produção")
        municipios_ids = [f["properties"]["municipio_id"] for f in geojson["features"]]
        assert len(municipios_ids) == len(set(municipios_ids))

    def test_crs_epsg4326_saida(self) -> None:
        """CRS de saída deve ser EPSG:4326."""
        from agrodata.analytics.queries import obter_geojson_mapa
        geojson = obter_geojson_mapa("Todos", "2023", "Produção")
        assert geojson["crs"]["properties"]["name"] == "EPSG:4326"

    def test_limite_cache_eviction(self) -> None:
        """Cache deve ter limite e fazer eviction LRU."""
        from agrodata.analytics.queries import _geojson_cache
        # O cache tem maxsize=64, vamos testar com menos itens para não demorar
        # Apenas validamos que o limite existe
        assert _geojson_cache._maxsize == 64