"""Componente de detalhe do município."""

from __future__ import annotations

import streamlit as st


def format_value(value: float | None, unit: str = "", decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{decimals}f} {unit}"


def render_municipio_detail(detail: dict | None) -> None:
    """Renderiza painel de detalhe do município."""
    if not detail:
        st.info("Selecione um município no mapa para ver os detalhes")
        return

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{detail.get('municipio_nome', '—')} ({detail.get('municipio_id', '—')})")
    with col2:
        st.write(f"**UF:** {detail.get('uf', '—')}")

    # Badges
    col1, col2, col3 = st.columns(3)
    with col1:
        cultura = detail.get('cultura', '—')
        st.write(f"**Cultura:** {cultura}")
    with col2:
        st.write(f"**Período:** {detail.get('periodo', '—')}")
    with col3:
        tem_dado = detail.get('tem_dado_agricola', False)
        badge = "✅ Tem dado agrícola" if tem_dado else "⚠️ Sem dado agrícola para o indicador"
        st.write(badge)

    # Métricas agrícolas
    st.markdown("### Dados Agrícolas")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Área Plantada", format_value(detail.get('area_plantada_ha'), "ha", 1))
    with col2:
        st.metric("Produção", format_value(detail.get('quantidade_produzida_t'), "t", 1))
    with col3:
        st.metric("Produtividade", format_value(detail.get('rendimento_medio_kg_ha'), "kg/ha", 1))
    with col4:
        valor_mil = detail.get('valor_producao_mil_reais')
        st.metric("Valor (mil R$)", format_value(valor_mil, "mil R$", 1))

    # Valor em reais (conversão derivada)
    valor_reais = detail.get('valor_producao_reais')
    if valor_reais is not None:
        st.metric("Valor da Produção (R$)", format_value(valor_reais, "R$", 0))

    # Área territorial
    area_km2 = detail.get('area_km2')
    if area_km2 is not None:
        st.metric("Área Territorial", format_value(area_km2, "km²", 2))

    # Ranking e percentil
    if detail.get('posicao_ranking') is not None or detail.get('percentil_indicador') is not None:
        st.markdown("### Posição no Ranking")
        col1, col2 = st.columns(2)
        with col1:
            pos = detail.get('posicao_ranking')
            st.metric("Posição", f"{pos}º" if pos else "—")
        with col2:
            pct = detail.get('percentil_indicador')
            st.metric("Percentil", f"{pct:.1f}%" if pct else "—")

    # Indicador de referência
    st.caption(f"Indicador de referência: {detail.get('indicador', '—')}")