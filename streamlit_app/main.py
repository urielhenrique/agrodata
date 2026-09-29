"""Streamlit App — MVP 1: IBGE PAM + Malha Municipal MG."""

from __future__ import annotations

import streamlit as st

from streamlit_app.components.insights import render_insights
from streamlit_app.components.kpis import render_kpis
from streamlit_app.components.map import render_mapa
from streamlit_app.components.municipality import render_municipio_detail
from streamlit_app.components.ranking import render_ranking
from streamlit_app.components.scatter import render_scatter
from streamlit_app.utils.api_client import (
    get_health,
    get_insights,
    get_kpis,
    get_mapa_geojson,
    get_municipio,
    get_ranking,
    get_scatter,
)

# Configuração da página
st.set_page_config(
    page_title="AgroData — MVP 1",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estado da sessão para município selecionado
if "municipio_selecionado" not in st.session_state:
    st.session_state.municipio_selecionado = None


def main():
    st.title("🌾 AgroData — Inteligência Territorial")
    st.caption("MVP 1: IBGE PAM 2023 (Soja e Milho) + Malha Municipal MG 2023")

    # Health check
    health = get_health()
    if not health or health.get("status") != "ok":
        st.error("API indisponível. Inicie o servidor FastAPI: `uvicorn agrodata.api.main:app --reload`")
        st.stop()

    # Sidebar - Filtros
    with st.sidebar:
        st.header("Filtros")

        cultura = st.selectbox(
            "Cultura",
            ["Todos", "Soja", "Milho"],
            index=0,
            help="Filtra observações agrícolas",
        )

        periodo = st.selectbox(
            "Período",
            ["2023"],
            index=0,
        )

        indicador = st.selectbox(
            "Indicador do Mapa",
            ["Produção", "Área", "Produtividade", "Valor da produção"],
            index=0,
            help="Controla a intensidade do coroplético e o ranking",
        )

        st.divider()

        # Data Lineage
        st.header("Origem dos Dados")
        st.markdown("""
        **Dados Agrícolas:** IBGE PAM 2023  
        **Geometria:** Malha Municipal IBGE 2023 (EPSG:4674 → 4326)  
        **Estados:** Minas Gerais  
        **Culturas:** Soja e Milho  
        **Período:** 2023
        """)

    # Carrega dados da API
    with st.spinner("Carregando dados..."):
        kpis = get_kpis(cultura, periodo, indicador)
        ranking = get_ranking(cultura, periodo, indicador)
        scatter = get_scatter(cultura, periodo)
        insights = get_insights(cultura, periodo, indicador, st.session_state.municipio_selecionado)
        geojson = get_mapa_geojson(cultura, periodo, indicador)

    # Layout principal
    # Linha 1: KPIs
    st.header("Indicadores Principais")
    render_kpis(kpis)

    # Linha 2: Mapa + Detalhe
    st.header("Mapa Coroplético")
    col_mapa, col_detalhe = st.columns([2, 1])

    with col_mapa:
        municipio_clicado = render_mapa(geojson, indicador)
        if municipio_clicado:
            st.session_state.municipio_selecionado = municipio_clicado
            st.rerun()

    with col_detalhe:
        # Busca detalhe do município selecionado
        if st.session_state.municipio_selecionado:
            detalhe = get_municipio(
                st.session_state.municipio_selecionado,
                cultura,
                periodo,
                indicador,
            )
            render_municipio_detail(detalhe)
        else:
            st.info("Clique em um município no mapa para ver detalhes")

    # Linha 3: Ranking + Scatter
    col_ranking, col_scatter = st.columns(2)

    with col_ranking:
        st.header("Ranking Top 10")
        render_ranking(ranking)

    with col_scatter:
        st.header("Área × Produtividade")
        render_scatter(scatter)

    # Linha 4: Insights
    st.header("Insights")
    render_insights(insights)

    # Rodapé
    st.divider()
    st.caption(
        "AgroData MVP 1 • Dados: IBGE PAM 2023 + Malha Municipal IBGE 2023 • "
        "Arquitetura: Streamlit → FastAPI → Analytics → GeoParquet • "
        "CRS Dados: EPSG:4674 | CRS Mapa: EPSG:4326"
    )


if __name__ == "__main__":
    main()