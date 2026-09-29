"""Endpoint para ranking Top N."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from agrodata.analytics.indicators import calcular_ranking
from agrodata.api.schemas import ErrorResponse, RankingItemResponse, RankingResponse

router = APIRouter()


@router.get(
    "/ranking",
    response_model=RankingResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna ranking Top N por indicador",
)
async def get_ranking(
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
    indicador: Annotated[str, Query(description="Indicador")] = "Produção",
    limite: Annotated[int, Query(ge=1, le=100, description="Número de municípios no ranking")] = 10,
) -> RankingResponse:
    """
    Retorna ranking Top N ordenado decrescentemente pelo indicador.

    Apenas municípios com dado válido para o indicador são considerados.
    Ausência de dado ≠ zero.
    """
    try:
        items_domain = calcular_ranking(cultura=cultura, periodo=periodo, indicador=indicador, limite=limite)
        items = [
            RankingItemResponse(
                posicao=item.posicao,
                municipio_id=item.municipio_id,
                municipio_nome=item.municipio_nome,
                uf=item.uf,
                valor=item.valor,
                cultura=item.cultura,
                indicador=item.indicador,
            )
            for item in items_domain
        ]
        return RankingResponse(
            items=items,
            cultura_filtro=cultura,
            indicador_filtro=indicador,
            periodo=periodo,
            limite=limite,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular ranking: {e!s}")