"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agrodata.api.schemas import ErrorResponse, HealthResponse
from agrodata.config import DatasetConfig

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Verifica saúde da API e disponibilidade dos datasets",
)
async def health_check() -> HealthResponse:
    """Verifica se a API está operacional e os datasets acessíveis."""
    try:
        DatasetConfig.validar_arquivos_existem()
        return HealthResponse(
            dataset_pam=str(DatasetConfig.PAM_INTEGRADO.name),
            dataset_malha=str(DatasetConfig.MALHA_TERRITORIAL.name),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))