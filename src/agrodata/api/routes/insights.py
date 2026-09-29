"""Endpoint para insights determinísticos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from agrodata.analytics.indicators import gerar_insights
from agrodata.api.schemas import ErrorResponse, IndicatorName, InsightsResponse

router = APIRouter()


@router.get(
    "/insights",
    response_model=InsightsResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna insights determinísticos para o filtro",
)
async def get_insights(
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
    indicador: Annotated[IndicatorName, Query(description="Indicador")] = "Produção",
    municipio_selecionado: Annotated[str | None, Query(min_length=7, max_length=7, description="Município selecionado para insight de percentil")] = None,
) -> InsightsResponse:
    """
    Retorna insights determinísticos:
    - Top 5 municípios (concentração)
    - Participação do Top 10 no total observado
    - Total de municípios com dado
    - Percentil do município selecionado (se informado)
    - Estatísticas do indicador (média, mediana, desvio)

    Não usa IA — todos os insights são cálculos diretos dos dados.
    """
    try:
        insights = gerar_insights(
            cultura=cultura,
            periodo=periodo,
            indicador=indicador,
            municipio_selecionado=municipio_selecionado,
        )
        return insights
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar insights: {e!s}")