"""Cliente HTTP para a API FastAPI."""

from __future__ import annotations

import httpx
import streamlit as st

API_BASE_URL = "http://localhost:8000/api"


@st.cache_data(ttl=60)
def _get(endpoint: str, params: dict | None = None) -> dict | None:
    """Faz GET na API com cache."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{API_BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        st.error(f"Erro na API ({e.response.status_code}): {e.response.text}")
        return None
    except httpx.RequestError as e:
        st.error(f"Erro de conexão com a API: {e!s}")
        return None


def get_health() -> dict | None:
    return _get("/health")


def get_kpis(cultura: str, periodo: str, indicador: str) -> dict | None:
    return _get("/kpis", {"cultura": cultura, "periodo": periodo, "indicador": indicador})


def get_ranking(cultura: str, periodo: str, indicador: str, limite: int = 10) -> dict | None:
    return _get("/ranking", {"cultura": cultura, "periodo": periodo, "indicador": indicador, "limite": limite})


def get_municipio(municipio_id: str, cultura: str, periodo: str, indicador: str) -> dict | None:
    return _get(f"/municipality/{municipio_id}", {"cultura": cultura, "periodo": periodo, "indicador": indicador})


def get_insights(cultura: str, periodo: str, indicador: str, municipio_selecionado: str | None = None) -> dict | None:
    params = {"cultura": cultura, "periodo": periodo, "indicador": indicador}
    if municipio_selecionado:
        params["municipio_selecionado"] = municipio_selecionado
    return _get("/insights", params)


def get_scatter(cultura: str, periodo: str) -> dict | None:
    return _get("/scatter", {"cultura": cultura, "periodo": periodo})


def get_mapa_geojson(cultura: str, periodo: str, indicador: str) -> dict | None:
    return _get("/map/geojson", {"cultura": cultura, "periodo": periodo, "indicador": indicador})