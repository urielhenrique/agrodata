"""Componente de KPIs."""

from __future__ import annotations

import streamlit as st


def format_number(value: float | None, decimals: int = 0, suffix: str = "") -> str:
    """Formata número para exibição."""
    if value is None:
        return "—"
    if decimals == 0:
        return f"{value:,.0f}{suffix}"
    return f"{value:,.{decimals}f}{suffix}"


def render_kpis(kpis: dict | None) -> None:
    """Renderiza cards de KPIs."""
    if not kpis:
        st.warning("KPIs não disponíveis")
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Área Total",
            format_number(kpis.get("area_total_ha"), 0, " ha"),
            help="Soma da área plantada dos municípios com dado",
        )

    with col2:
        st.metric(
            "Produção Total",
            format_number(kpis.get("producao_total_t"), 0, " t"),
            help="Soma da quantidade produzida dos municípios com dado",
        )

    with col3:
        prod = kpis.get("produtividade_ponderada_kg_ha")
        st.metric(
            "Produtividade Ponderada",
            format_number(prod, 1, " kg/ha"),
            help="Produção total (kg) / Área total (ha) — não é média simples",
        )

    with col4:
        valor = kpis.get("valor_total_producao_reais")
        st.metric(
            "Valor da Produção",
            format_number(valor, 0, " R$"),
            help="Soma do valor da produção (valor_mil_reais × 1.000)",
        )

    with col5:
        st.metric(
            "Municípios com Dado",
            format_number(kpis.get("municipios_com_dado"), 0),
            help="Municípios com observação válida para o indicador filtrado",
        )

    # Detalhes adicionais
    with st.expander("Detalhes dos KPIs"):
        st.write(f"**Cultura filtrada:** {kpis.get('cultura_filtro', '—')}")
        st.write(f"**Indicador:** {kpis.get('indicador_filtro', '—')}")
        st.write(f"**Período:** {kpis.get('periodo', '—')}")
        st.write(f"**Valor em mil reais (original):** {kpis.get('valor_total_producao_mil_reais', 0):,.0f}")