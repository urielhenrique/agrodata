"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agrodata.api.routes import health as health_routes
from agrodata.api.routes import insights as insights_routes
from agrodata.api.routes import kpis as kpis_routes
from agrodata.api.routes import map as map_routes
from agrodata.api.routes import municipality as municipality_routes
from agrodata.api.routes import ranking as ranking_routes
from agrodata.api.routes import scatter as scatter_routes
from agrodata.config import DatasetConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicação."""
    # Startup
    DatasetConfig.validar_arquivos_existem()
    yield
    # Shutdown
    from agrodata.analytics.queries import limpar_cache
    limpar_cache()


def criar_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI."""
    app = FastAPI(
        title="AgroData API",
        description="API para inteligência territorial agrícola - MVP 1: IBGE PAM + Malha Municipal MG",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS para Streamlit
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, restringir
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Inclui rotas
    app.include_router(health_routes.router, prefix="/api", tags=["Health"])
    app.include_router(map_routes.router, prefix="/api", tags=["Mapa"])
    app.include_router(kpis_routes.router, prefix="/api", tags=["KPIs"])
    app.include_router(ranking_routes.router, prefix="/api", tags=["Ranking"])
    app.include_router(municipality_routes.router, prefix="/api", tags=["Município"])
    app.include_router(insights_routes.router, prefix="/api", tags=["Insights"])
    app.include_router(scatter_routes.router, prefix="/api", tags=["Scatter"])

    return app


app = criar_app()