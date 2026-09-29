"""Endpoint para dados do gráfico Área × Produtividade."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from agrodata.analytics.queries import obter_scatter_data
from agrodata.api.schemas import ErrorResponse, ScatterPointResponse, ScatterResponse

router = APIRouter()


@router.get(
    "/scatter",
    response_model=ScatterResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna dados para gráfico Área × Produtividade",
)
async def get_scatter(
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
) -> ScatterResponse:
    """
    Retorna pontos para scatter plot Área (ha) × Produtividade (kg/ha).

    Cada ponto = um município × cultura.
    Apenas municípios com área > 0 e produtividade > 0.
    Não classifica como bom/ruim — apenas visualização.
    """
    try:
        points_domain = obter_scatter_data(cultura=cultura, periodo=periodo)
        points = [
            ScatterPointResponse(
                municipio_id=p.municipio_id,
                municipio_nome=p.municipio_nome,
                uf=p.uf,
                area_plantada_ha=p.area_plantada_ha,
                rendimento_medio_kg_ha=p.rendimento_medio_kg_ha,
                cultura=p.cultura,
            )
            for p in points_domain
        ]
        return ScatterResponse(
            points=points,
            cultura_filtro=cultura,
            periodo=periodo,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter scatter: {e!s}")