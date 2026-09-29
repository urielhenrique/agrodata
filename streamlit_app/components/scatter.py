"""Componente de gráfico Área × Produtividade."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


def render_scatter(scatter_data: dict | None) -> None:
    """Renderiza gráfico scatter Área × Produtividade."""
    if not scatter_data or not scatter_data.get("points"):
        st.info("Dados para scatter não disponíveis")
        return

    points = scatter_data["points"]
    df = pd.DataFrame(points)

    if df.empty:
        st.info("Nenhum ponto para exibir")
        return

    # Cria gráfico
    fig = px.scatter(
        df,
        x="area_plantada_ha",
        y="rendimento_medio_kg_ha",
        color="cultura",
        hover_data=["municipio_nome", "uf"],
        labels={
            "area_plantada_ha": "Área Plantada (ha)",
            "rendimento_medio_kg_ha": "Produtividade (kg/ha)",
            "cultura": "Cultura",
        },
        title="Área Plantada × Produtividade por Município",
    )

    fig.update_traces(marker={"size": 8, "opacity": 0.7})
    fig.update_layout(
        xaxis_title="Área Plantada (ha)",
        yaxis_title="Produtividade (kg/ha)",
        legend_title="Cultura",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Cada ponto = um município × cultura. "
        f"Total: {len(df)} observações. "
        f"Cultura filtrada: {scatter_data.get('cultura_filtro', '—')} | Período: {scatter_data.get('periodo', '—')}"
    )