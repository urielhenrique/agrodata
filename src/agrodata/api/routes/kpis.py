"""Endpoint para KPIs agregados."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from agrodata.analytics.indicators import calcular_kpis
from agrodata.api.schemas import ErrorResponse, IndicatorName, KPIResponse

router = APIRouter()


@router.get(
    "/kpis",
    response_model=KPIResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna KPIs agregados para o filtro",
)
async def get_kpis(
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
    indicador: Annotated[IndicatorName, Query(description="Indicador de referência")] = "Produção",
) -> KPIResponse:
    """
    Calcula KPIs:
    - Área total (ha)
    - Produção total (t)
    - Produtividade ponderada (kg/ha) = soma(produção) / soma(área)
    - Valor total da produção (reais) = valor_mil_reais * 1000
    - Municípios com dado agrícola
    """
    try:
        kpis = calcular_kpis(cultura=cultura, periodo=periodo, indicador=indicador)
        return kpis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular KPIs: {e!s}")