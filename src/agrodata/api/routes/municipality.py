"""Endpoint para detalhe de município."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from agrodata.analytics.queries import obter_municipio_detalhe
from agrodata.api.schemas import ErrorResponse, IndicatorName, MunicipalityDetailResponse

router = APIRouter()


@router.get(
    "/municipality/{municipio_id}",
    response_model=MunicipalityDetailResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Retorna detalhe completo de um município",
)
async def get_municipio(
    municipio_id: Annotated[str, Path(min_length=7, max_length=7, description="Código IBGE do município (7 dígitos)")],
    cultura: Annotated[str, Query(description="Cultura: Todos, Soja, Milho")] = "Todos",
    periodo: Annotated[str, Query(description="Período")] = "2023",
    indicador: Annotated[IndicatorName, Query(description="Indicador para percentil/ranking")] = "Produção",
) -> MunicipalityDetailResponse:
    """
    Retorna detalhe completo do município para painel lateral.

    Inclui:
    - Dados agrícolas (área, produção, produtividade, valor)
    - Conversão valor_mil_reais → reais (apenas para apresentação)
    - Percentil e posição no ranking do indicador
    - Flag tem_dado_agricola (ausência ≠ zero)
    """
    try:
        detalhe = obter_municipio_detalhe(municipio_id, cultura, periodo, indicador)
        if detalhe is None:
            raise HTTPException(status_code=404, detail=f"Município {municipio_id} não encontrado")
        return detalhe
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar município: {e!s}")