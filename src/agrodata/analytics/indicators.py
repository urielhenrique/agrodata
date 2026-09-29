"""Cálculo de indicadores, rankings e insights determinísticos."""

from __future__ import annotations

from agrodata.analytics.models import (
    CropFilter,
    IndicatorName,
    InsightItem,
    InsightsResponse,
    KPIsResponse,
    RankingItem,
)
from agrodata.analytics.queries import (
    obter_dados_filtrados,
    obter_kpis,
    obter_ranking,
)
from agrodata.config import DatasetConfig


def calcular_kpis(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
) -> KPIsResponse:
    """Calcula KPIs agregados."""
    kpis_dict = obter_kpis(cultura, periodo, indicador)
    return KPIsResponse(**kpis_dict)


def calcular_ranking(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
    limite: int = 10,
) -> list[RankingItem]:
    """Calcula ranking Top N."""
    ranking_data = obter_ranking(cultura, periodo, indicador, limite)
    return [RankingItem(**item) for item in ranking_data]


def _calcular_participacao_top10(
    gdf_filtrado,
    coluna_indicador: str,
    top_n: int = 10,
) -> float:
    """Calcula participação do Top N no total observado."""
    gdf_valido = gdf_filtrado[gdf_filtrado[coluna_indicador].notna()].copy()
    if gdf_valido.empty:
        return 0.0

    total = gdf_valido[coluna_indicador].sum()
    if total == 0:
        return 0.0

    top_valores = gdf_valido.nlargest(top_n, coluna_indicador)[coluna_indicador].sum()
    return float(top_valores / total * 100)


def _calcular_concentracao_maiores(
    gdf_filtrado,
    coluna_indicador: str,
    top_n: int = 5,
) -> list[str]:
    """Retorna nomes dos top N municípios por indicador."""
    gdf_valido = gdf_filtrado[gdf_filtrado[coluna_indicador].notna()].copy()
    if gdf_valido.empty:
        return []

    top = gdf_valido.nlargest(top_n, coluna_indicador)
    return top["municipio_nome"].tolist()


def gerar_insights(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
    municipio_selecionado: str | None = None,
) -> InsightsResponse:
    """Gera insights determinísticos para o filtro atual."""
    from agrodata.config import DatasetConfig as Cfg

    gdf = obter_dados_filtrados(cultura, periodo)
    coluna_indicador = DatasetConfig.INDICADORES[indicador]

    gdf_valido = gdf[gdf[coluna_indicador].notna()].copy()
    insights = []

    if gdf_valido.empty:
        return InsightsResponse(
            insights=[],
            cultura_filtro=cultura,
            indicador_filtro=indicador,
            periodo=periodo,
        )

    # 1. Concentração - maiores municípios
    maiores = _calcular_concentracao_maiores(gdf_valido, coluna_indicador, 5)
    if maiores:
        insights.append(InsightItem(
            titulo=f"Top 5 municípios em {indicador}",
            descricao="Municípios com maiores valores observados: " + ", ".join(maiores),
            valor=maiores,
            tipo="concentracao",
        ))

    # 2. Participação do Top 10
    participacao = _calcular_participacao_top10(gdf_valido, coluna_indicador, 10)
    insights.append(InsightItem(
        titulo="Participação do Top 10",
        descricao=f"Os 10 maiores municípios concentram {participacao:.1f}% do {indicador.lower()} total observado",
        valor=round(participacao, 1),
        tipo="participacao",
    ))

    # 3. Estatísticas gerais
    total_municipios = gdf_valido[Cfg.COLUNA_MUNICIPIO_ID].nunique()
    insights.append(InsightItem(
        titulo="Municípios com dado agrícola",
        descricao=f"{total_municipios} municípios possuem observação válida para {indicador.lower()} em {periodo}",
        valor=int(total_municipios),
        tipo="estatistica",
    ))

    # 4. Percentil do município selecionado (se houver)
    if municipio_selecionado:
        from agrodata.analytics.queries import obter_municipio_detalhe
        detalhe = obter_municipio_detalhe(municipio_selecionado, cultura, periodo, indicador)
        if detalhe and detalhe.percentil_indicador is not None:
            insights.append(InsightItem(
                titulo=f"Posição de {detalhe.municipio_nome}",
                descricao=f"Está no percentil {detalhe.percentil_indicador:.1f} (posição {detalhe.posicao_ranking} de {gdf_valido[Cfg.COLUNA_MUNICIPIO_ID].nunique()}) no ranking de {indicador.lower()}",
                valor=round(detalhe.percentil_indicador, 1),
                tipo="percentil",
            ))

    # 5. Estatísticas do indicador
    valores = gdf_valido[coluna_indicador].dropna()
    if len(valores) > 0:
        media = float(valores.mean())
        mediana = float(valores.median())
        desvio = float(valores.std())
        insights.append(InsightItem(
            titulo=f"Estatísticas de {indicador}",
            descricao=f"Média: {media:,.2f} | Mediana: {mediana:,.2f} | Desvio padrão: {desvio:,.2f}",
            valor={"media": round(media, 2), "mediana": round(mediana, 2), "desvio_padrao": round(desvio, 2)},
            tipo="estatistica",
        ))

    return InsightsResponse(
        insights=insights,
        cultura_filtro=cultura,
        indicador_filtro=indicador,
        periodo=periodo,
    )