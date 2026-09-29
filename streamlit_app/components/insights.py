"""Componente de insights determinísticos."""

from __future__ import annotations

import streamlit as st


def render_insights(insights_data: dict | None) -> None:
    """Renderiza painel de insights."""
    if not insights_data or not insights_data.get("insights"):
        st.info("Insights não disponíveis")
        return

    insights = insights_data["insights"]

    for insight in insights:
        tipo = insight.get("tipo", "")
        titulo = insight.get("titulo", "")
        descricao = insight.get("descricao", "")
        valor = insight.get("valor")

        # Ícone por tipo
        icones = {
            "concentracao": "🎯",
            "participacao": "📊",
            "percentil": "📈",
            "estatistica": "📐",
        }
        icone = icones.get(tipo, "💡")

        with st.container():
            col1, col2 = st.columns([1, 10])
            with col1:
                st.markdown(f"### {icone}")
            with col2:
                st.markdown(f"**{titulo}**")
                st.write(descricao)
                if valor is not None and not isinstance(valor, (list, dict)):
                    st.caption(f"Valor: {valor}")

    st.caption(
        f"Insights determinísticos calculados diretamente dos dados. "
        f"Cultura: {insights_data.get('cultura_filtro')} | Indicador: {insights_data.get('indicador_filtro')} | Período: {insights_data.get('periodo')}"
    )