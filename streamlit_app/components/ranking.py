"""Componente de Ranking Top N."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_ranking(ranking_data: dict | None) -> None:
    """Renderiza tabela de ranking."""
    if not ranking_data or not ranking_data.get("items"):
        st.info("Ranking não disponível")
        return

    items = ranking_data["items"]
    df = pd.DataFrame(items)

    # Renomeia colunas para exibição
    df_display = df[["posicao", "municipio_nome", "uf", "valor", "cultura"]].copy()
    df_display.columns = ["Pos.", "Município", "UF", "Valor", "Cultura"]

    # Formata valor
    df_display["Valor"] = df_display["Valor"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "—")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pos.": st.column_config.NumberColumn("Pos.", width="small"),
            "Município": st.column_config.TextColumn("Município", width="medium"),
            "UF": st.column_config.TextColumn("UF", width="small"),
            "Valor": st.column_config.TextColumn("Valor", width="medium"),
            "Cultura": st.column_config.TextColumn("Cultura", width="small"),
        },
    )

    st.caption(f"Top {ranking_data.get('limite', 10)} | Cultura: {ranking_data.get('cultura_filtro')} | Indicador: {ranking_data.get('indicador_filtro')} | Período: {ranking_data.get('periodo')}")