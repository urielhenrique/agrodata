"""Modelos de domínio da camada Analytics — independentes de HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CropFilter = Literal["Todos", "Soja", "Milho"]
IndicatorName = Literal["Produção", "Área", "Produtividade", "Valor da produção"]


@dataclass(frozen=True)
class MunicipalityIdentifier:
    """Identificador de município."""
    municipio_id: str
    municipio_nome: str
    uf: str


@dataclass(frozen=True)
class AgriculturalObservation:
    """Uma observação agrícola: município × produto × período."""
    municipio_id: str
    municipio_nome: str
    uf: str
    produto_codigo: str
    produto_nome: str
    periodo: str
    area_plantada_ha: float | None
    quantidade_produzida_t: float | None
    rendimento_medio_kg_ha: float | None
    valor_producao_mil_reais: float | None
    geometry: any  # shapely geometry
    area_km2: float | None


@dataclass(frozen=True)
class KPIsResponse:
    """KPIs agregados para o filtro atual."""
    area_total_ha: float
    producao_total_t: float
    produtividade_ponderada_kg_ha: float | None
    valor_total_producao_reais: float
    valor_total_producao_mil_reais: float
    municipios_com_dado: int
    cultura_filtro: str
    indicador_filtro: str
    periodo: str


@dataclass(frozen=True)
class RankingItem:
    """Item do ranking Top N."""
    posicao: int
    municipio_id: str
    municipio_nome: str
    uf: str
    valor: float | None
    cultura: str
    indicador: str


@dataclass(frozen=True)
class MunicipalityDetail:
    """Detalhe completo de um município para o painel lateral."""
    municipio_id: str
    municipio_nome: str
    uf: str
    cultura: str
    periodo: str
    area_plantada_ha: float | None
    quantidade_produzida_t: float | None
    rendimento_medio_kg_ha: float | None
    valor_producao_mil_reais: float | None
    valor_producao_reais: float | None
    area_km2: float | None
    tem_dado_agricola: bool
    percentil_indicador: float | None
    posicao_ranking: int | None
    indicador: str


@dataclass(frozen=True)
class ScatterPoint:
    """Ponto para gráfico Área × Produtividade."""
    municipio_id: str
    municipio_nome: str
    uf: str
    area_plantada_ha: float
    rendimento_medio_kg_ha: float
    cultura: str


@dataclass(frozen=True)
class InsightItem:
    """Um insight determinístico."""
    titulo: str
    descricao: str
    valor: str | float | list[str] | dict | None
    tipo: Literal["concentracao", "participacao", "percentil", "estatistica"]


@dataclass(frozen=True)
class InsightsResponse:
    """Coleção de insights para o filtro atual."""
    insights: list[InsightItem]
    cultura_filtro: str
    indicador_filtro: str
    periodo: str


@dataclass(frozen=True)
class MapFeature:
    """Feature GeoJSON para o mapa coroplético."""
    type: str = "Feature"
    geometry: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MapGeoJSONResponse:
    """Resposta completa do mapa (FeatureCollection)."""
    type: str = "FeatureCollection"
    features: list[MapFeature] = field(default_factory=list)
    crs: dict = field(default_factory=lambda: {"type": "name", "properties": {"name": "EPSG:4326"}})
    indicador: str = ""
    cultura: str = ""
    periodo: str = ""


@dataclass(frozen=True)
class HealthResponse:
    """Health check da API."""
    status: str = "ok"
    dataset_pam: str = ""
    dataset_malha: str = ""
    crs_dados: str = "EPSG:4674"
    crs_api: str = "EPSG:4326"