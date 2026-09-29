"""Endpoint para GeoJSON do mapa coroplético."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from agrodata.analytics.queries import obter_geojson_mapa
from agrodata.api.schemas import ErrorResponse, IndicatorName, MapGeoJSONResponse

router = APIRouter()


@router.get(
    "/map/geojson",
    response_model=MapGeoJSONResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna FeatureCollection GeoJSON para mapa coroplético (EPSG:4326)",
)
async def get_mapa_geojson(
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
    indicador: Annotated[IndicatorName, Query(description="Indicador para intensidade do mapa")] = "Produção",
) -> MapGeoJSONResponse:
    """
    Retorna FeatureCollection GeoJSON reprojetado para EPSG:4326.

    A geometria é reprojetada de EPSG:4674 (dados) para EPSG:4326 (mapa).
    Apenas municípios com dado agrícola válido para o indicador são incluídos.
    """
    try:
        geojson = obter_geojson_mapa(cultura=cultura, periodo=periodo, indicador=indicador)
        return MapGeoJSONResponse(**geojson)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar mapa: {e!s}")