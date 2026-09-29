"""Componente de mapa coroplético com Folium."""

from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium


def _get_color_scale(valor: float | None, min_val: float, max_val: float) -> str:
    """Retorna cor baseada no valor normalizado (viridis-like)."""
    if valor is None:
        return "#cccccc"
    if max_val == min_val:
        return "#440154"
    norm = (valor - min_val) / (max_val - min_val)
    # Viridis aproximado
    if norm < 0.25:
        r, g, b = 68, 1, 84
    elif norm < 0.5:
        r, g, b = 59, 82, 139
    elif norm < 0.75:
        r, g, b = 33, 145, 140
    else:
        r, g, b = 94, 201, 98
    return f"#{r:02x}{g:02x}{b:02x}"


def render_mapa(geojson_data: dict | None, indicador: str) -> str | None:
    """
    Renderiza mapa coroplético Folium.

    Retorna municipio_id do município clicado (se houver).
    """
    if not geojson_data or not geojson_data.get("features"):
        st.warning("Dados do mapa não disponíveis")
        return None

    features = geojson_data["features"]

    # Calcula min/max para escala de cores
    valores = [f["properties"].get("valor") for f in features if f["properties"].get("valor") is not None]
    min_val = min(valores) if valores else 0
    max_val = max(valores) if valores else 1

    # Cria mapa base centrado em MG
    m = folium.Map(
        location=[-18.5, -44.0],
        zoom_start=6,
        tiles="CartoDB positron",
    )

    # Adiciona features
    for feature in features:
        props = feature["properties"]
        valor = props.get("valor")
        municipio_id = props.get("municipio_id")
        municipio_nome = props.get("municipio_nome")

        color = _get_color_scale(valor, min_val, max_val)

        # Tooltip
        tooltip_text = f"{municipio_nome} ({municipio_id})"
        if valor is not None:
            tooltip_text += f"\n{indicador}: {valor:,.2f}"

        folium.GeoJson(
            feature["geometry"],
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": "#555555",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
            highlight_function=lambda x: {
                "fillColor": "#ffff00",
                "color": "#000000",
                "weight": 2,
                "fillOpacity": 0.9,
            },
            tooltip=folium.Tooltip(tooltip_text, sticky=True),
        ).add_to(m)

    # Legenda
    legend_html = f"""
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000; 
                background-color: white; padding: 10px; border: 1px solid gray; 
                border-radius: 5px; font-size: 12px;">
        <b>{indicador}</b><br>
        <i style="background:#440154;width:18px;height:18px;display:inline-block;"></i> Baixo<br>
        <i style="background:#3b528b;width:18px;height:18px;display:inline-block;"></i> Médio<br>
        <i style="background:#21918c;width:18px;height:18px;display:inline-block;"></i> Alto<br>
        <i style="background:#5ec962;width:18px;height:18px;display:inline-block;"></i> Muito Alto<br>
        <i style="background:#cccccc;width:18px;height:18px;display:inline-block;"></i> Sem dado
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Renderiza
    map_data = st_folium(
        m,
        width=700,
        height=500,
        returned_objects=["last_clicked"],
        key="mapa_coropletico",
    )

    # Retorna municipio_id se clicado
    if map_data and map_data.get("last_clicked"):
        return map_data["last_clicked"].get("municipio_id")

    return None


def render_mapa_legenda(geojson_data: dict | None) -> None:
    """Renderiza apenas a legenda do mapa (para uso fora do st_folium)."""
    if not geojson_data:
        return