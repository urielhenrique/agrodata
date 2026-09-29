"""Schemas Pydantic para a API HTTP — contratos de request/response."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Valores permitidos (devem espelhar analytics/models.py)
CropFilter = Literal["Todos", "Soja", "Milho"]
IndicatorName = Literal["Produção", "Área", "Produtividade", "Valor da produção"]


# ============================================================================
# Request Parameters (Query params compartilhados)
# ============================================================================


class FiltrosBase(BaseModel):
    """Filtros base para endpoints."""
    cultura: CropFilter = Field(default="Todos", description="Filtro de cultura")
    periodo: str = Field(default="2023", description="Período de referência")
    indicador: IndicatorName = Field(default="Produção", description="Indicador para mapa/ranking")


# ============================================================================
# Response Models (espelham analytics/models mas com tipos JSON-serializáveis)
# ============================================================================


class KPIResponse(BaseModel):
    """KPIs agregados."""
    area_total_ha: float
    producao_total_t: float
    produtividade_ponderada_kg_ha: float | None = None
    valor_total_producao_reais: float
    valor_total_producao_mil_reais: float
    municipios_com_dado: int
    cultura_filtro: str
    indicador_filtro: str
    periodo: str


class RankingItemResponse(BaseModel):
    """Item do ranking."""
    posicao: int
    municipio_id: str
    municipio_nome: str
    uf: str
    valor: float | None = None
    cultura: str
    indicador: str


class RankingResponse(BaseModel):
    """Resposta do ranking."""
    items: list[RankingItemResponse]
    cultura_filtro: str
    indicador_filtro: str
    periodo: str
    limite: int


class MunicipalityDetailResponse(BaseModel):
    """Detalhe do município."""
    municipio_id: str
    municipio_nome: str
    uf: str
    cultura: str
    periodo: str
    area_plantada_ha: float | None = None
    quantidade_produzida_t: float | None = None
    rendimento_medio_kg_ha: float | None = None
    valor_producao_mil_reais: float | None = None
    valor_producao_reais: float | None = None
    area_km2: float | None = None
    tem_dado_agricola: bool
    percentil_indicador: float | None = None
    posicao_ranking: int | None = None
    indicador: str


class ScatterPointResponse(BaseModel):
    """Ponto para scatter plot."""
    municipio_id: str
    municipio_nome: str
    uf: str
    area_plantada_ha: float
    rendimento_medio_kg_ha: float
    cultura: str


class ScatterResponse(BaseModel):
    """Dados para gráfico Área × Produtividade."""
    points: list[ScatterPointResponse]
    cultura_filtro: str
    periodo: str


class InsightItemResponse(BaseModel):
    """Insight determinístico."""
    titulo: str
    descricao: str
    valor: str | float | list[str] | dict | None = None
    tipo: Literal["concentracao", "participacao", "percentil", "estatistica"]


class InsightsResponse(BaseModel):
    """Insights determinísticos."""
    insights: list[InsightItemResponse]
    cultura_filtro: str
    indicador_filtro: str
    periodo: str


class MapFeatureProperties(BaseModel):
    """Propriedades da feature do mapa."""
    municipio_id: str
    municipio_nome: str
    uf: str
    valor: float | None = None
    cultura: str


class MapFeatureResponse(BaseModel):
    """Feature GeoJSON."""
    type: str = "Feature"
    geometry: dict
    properties: MapFeatureProperties


class MapGeoJSONResponse(BaseModel):
    """FeatureCollection GeoJSON para mapa coroplético."""
    type: str = "FeatureCollection"
    features: list[MapFeatureResponse]
    crs: dict = {"type": "name", "properties": {"name": "EPSG:4326"}}
    indicador: str
    cultura: str
    periodo: str


class HealthResponse(BaseModel):
    """Health check."""
    status: str = "ok"
    dataset_pam: str
    dataset_malha: str
    crs_dados: str = "EPSG:4674"
    crs_api: str = "EPSG:4326"


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    detail: str
    codigo: str | None = None