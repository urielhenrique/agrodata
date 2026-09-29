"""Camada de acesso a dados — queries sobre os GeoParquets processados."""

from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
from typing import Any

import geopandas as gpd
import pandas as pd

from agrodata.analytics.models import (
    CropFilter,
    IndicatorName,
    MunicipalityDetail,
    ScatterPoint,
)
from agrodata.config import DatasetConfig
from agrodata.config import DatasetConfig as Cfg


class LRUCache:
    """Cache LRU simples em memória com limite de tamanho."""

    def __init__(self, maxsize: int = 64) -> None:
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


_geojson_cache = LRUCache(maxsize=64)


def _obter_chave_cache(
    cultura: CropFilter,
    periodo: str,
    indicador: IndicatorName,
) -> str:
    """Gera chave de cache baseada em dataset hash + parâmetros da query."""
    dataset_hash = DatasetConfig.obter_dataset_hash()
    return f"{dataset_hash}:{cultura}:{periodo}:{indicador}"


def limpar_cache_geojson() -> None:
    """Limpa o cache de GeoJSON (útil para testes)."""
    _geojson_cache.clear()


# Cache do dataset carregado (apenas leitura)
@lru_cache(maxsize=1)
def _carregar_pam_integrado() -> gpd.GeoDataFrame:
    """Carrega o PAM integrado com geometria (EPSG:4674)."""
    DatasetConfig.validar_arquivos_existem()
    gdf = gpd.read_parquet(DatasetConfig.PAM_INTEGRADO)
    # Garante CRS correto
    if gdf.crs is None or gdf.crs.to_epsg() != 4674:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    return gdf


@lru_cache(maxsize=1)
def _carregar_malha_territorial() -> gpd.GeoDataFrame:
    """Carrega a malha territorial completa (EPSG:4674)."""
    DatasetConfig.validar_arquivos_existem()
    gdf = gpd.read_parquet(DatasetConfig.MALHA_TERRITORIAL)
    if gdf.crs is None or gdf.crs.to_epsg() != 4674:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    return gdf


def _filtrar_por_cultura(
    gdf: gpd.GeoDataFrame,
    cultura: CropFilter,
) -> gpd.GeoDataFrame:
    """Filtra observações pela cultura selecionada."""
    if cultura == "Todos":
        return gdf
    produto_nome_alvo = DatasetConfig.PRODUTOS_VALIDOS[cultura]
    return gdf[gdf[Cfg.COLUNA_PRODUTO_NOME] == produto_nome_alvo].copy()


def _filtrar_por_periodo(
    gdf: gpd.GeoDataFrame,
    periodo: str,
) -> gpd.GeoDataFrame:
    """Filtra observações pelo período."""
    return gdf[gdf[Cfg.COLUNA_PERIODO] == periodo].copy()


def obter_dados_filtrados(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
) -> gpd.GeoDataFrame:
    """
    Retorna GeoDataFrame filtrado por cultura e período.

    Não modifica os dados originais. Retorna cópia.
    """
    gdf = _carregar_pam_integrado()
    gdf = _filtrar_por_cultura(gdf, cultura)
    gdf = _filtrar_por_periodo(gdf, periodo)
    return gdf.copy()


def _agregar_por_municipio(
    gdf: gpd.GeoDataFrame,
    cultura: CropFilter,
    indicador: IndicatorName,
) -> gpd.GeoDataFrame:
    """
    Agrega observações PAM por município.

    Para cultura única (Milho/Soja): retorna como está (já é 1 linha por município).
    Para "Todos": agrega soja + milho por município.
    """
    if cultura != "Todos":
        return gdf.copy()

    # Para "Todos", agrupa por município
    colunas_geo = ["municipio_id", "municipio_nome", "uf", "geometry", "area_km2"]
    colunas_valor = [
        "area_plantada_ha",
        "quantidade_produzida_t",
        "valor_producao_mil_reais",
        "rendimento_medio_kg_ha",
    ]

    # Garante que todas as colunas existem
    colunas_necessarias = colunas_geo + colunas_valor + ["produto_nome"]
    faltando = [c for c in colunas_necessarias if c not in gdf.columns]
    if faltando:
        raise ValueError(f"Colunas faltando para agregação: {faltando}")

    # Agrega por município
    agg_dict = {
        "municipio_nome": "first",
        "uf": "first",
        "geometry": "first",
        "area_km2": "first",
        "area_plantada_ha": "sum",
        "quantidade_produzida_t": "sum",
        "valor_producao_mil_reais": "sum",
        # rendimento_medio_kg_ha será recalculado como ponderado
    }

    gdf_agg = gdf.groupby("municipio_id", as_index=False).agg(agg_dict)

    # Recalcula produtividade ponderada: (produção_total / área_total) * 1000
    # produção em toneladas, área em hectares -> kg/ha
    gdf_agg["rendimento_medio_kg_ha"] = (
        gdf_agg["quantidade_produzida_t"] / gdf_agg["area_plantada_ha"] * 1000
    ).where(gdf_agg["area_plantada_ha"] > 0, None)

    # Mantém produto_nome como "Soja e Milho" para "Todos"
    gdf_agg["produto_nome"] = "Soja e Milho"
    gdf_agg["produto_codigo"] = "40122,40124"

    # Garante que é GeoDataFrame com CRS correto
    gdf_agg = gpd.GeoDataFrame(gdf_agg, geometry="geometry", crs=gdf.crs)

    return gdf_agg


def _simplificar_geometria_para_mapa(
    gdf: gpd.GeoDataFrame,
    tolerancia: float = 0.0005,
) -> gpd.GeoDataFrame:
    """
    Simplifica geometrias para exibição em mapa web.

    A tolerância padrão (0.0005 graus ≈ 55 metros no equador) é adequada
    para visualização em escala municipal (zoom 6-10).

    Não modifica os dados originais - retorna cópia com geometria simplificada.
    """
    gdf_simp = gdf.copy()

    # Simplifica sem preservar topologia (mais rápido, geometrias permanecem válidas)
    gdf_simp["geometry"] = gdf_simp.geometry.simplify(
        tolerance=tolerancia,
        preserve_topology=False,
    )

    # Remove geometrias que ficaram inválidas após simplificação
    invalidos = ~gdf_simp.geometry.is_valid
    if invalidos.any():
        # Tenta corrigir com buffer(0) apenas nos inválidos
        gdf_simp.loc[invalidos, "geometry"] = (
            gdf_simp.loc[invalidos, "geometry"].buffer(0)
        )

    return gdf_simp


def _preparar_geodataframe_para_mapa(
    gdf: gpd.GeoDataFrame,
    simplificar: bool = True,
    tolerancia: float = 0.0005,
) -> gpd.GeoDataFrame:
    """
    Prepara GeoDataFrame para consumo pelo mapa web.

    - Reprojeta para EPSG:4326
    - Opcionalmente simplifica geometrias
    """
    gdf = gdf.copy()

    # Reprojeta para EPSG:4326 apenas para consumo pelo mapa
    if gdf.crs and gdf.crs.to_epsg() == 4674:
        gdf = gdf.to_crs("EPSG:4326")

    if simplificar:
        gdf = _simplificar_geometria_para_mapa(gdf, tolerancia)

    return gdf


def obter_dados_para_mapa(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
) -> gpd.GeoDataFrame:
    """
    Retorna dados prontos para mapa coroplético (reprojetado para EPSG:4326).

    Inclui apenas municípios com dado agrícola válido para o indicador.
    Para "Todos", agrega soja + milho por município (uma feature por município).
    """
    gdf = obter_dados_filtrados(cultura, periodo)

    coluna_indicador = DatasetConfig.INDICADORES[indicador]

    # Remove municípios sem dado para o indicador (ausência ≠ zero)
    gdf = gdf[gdf[coluna_indicador].notna()].copy()

    # Agrega por município se necessário
    gdf = _agregar_por_municipio(gdf, cultura, indicador)

    # Prepara para mapa: reprojeta e simplifica
    gdf = _preparar_geodataframe_para_mapa(gdf, simplificar=True)

    return gdf


def obter_todos_municipios_territoriais() -> gpd.GeoDataFrame:
    """Retorna a malha territorial completa (853 municípios) em EPSG:4326."""
    gdf = _carregar_malha_territorial()
    if gdf.crs and gdf.crs.to_epsg() == 4674:
        gdf = gdf.to_crs("EPSG:4326")
    return gdf


def obter_municipio_detalhe(
    municipio_id: str,
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
) -> MunicipalityDetail | None:
    """Retorna detalhe completo de um município."""
    gdf = obter_dados_filtrados(cultura, periodo)

    if municipio_id not in gdf[Cfg.COLUNA_MUNICIPIO_ID].values:
        # Verifica se existe na malha territorial (pode não ter PAM)
        malha = _carregar_malha_territorial()
        if municipio_id not in malha[Cfg.COLUNA_MUNICIPIO_ID].values:
            return None

    # Filtra observação específica (municipio_id + cultura se aplicável)
    if cultura == "Todos":
        # Se "Todos", pode haver duas linhas (soja + milho). Retorna a primeira com dado do indicador.
        coluna_indicador = DatasetConfig.INDICADORES[indicador]
        obs = gdf[
            (gdf[Cfg.COLUNA_MUNICIPIO_ID] == municipio_id)
            & (gdf[coluna_indicador].notna())
        ].head(1)
    else:
        obs = gdf[gdf[Cfg.COLUNA_MUNICIPIO_ID] == municipio_id].head(1)

    if obs.empty:
        return None

    row = obs.iloc[0]
    coluna_indicador = DatasetConfig.INDICADORES[indicador]
    valor_indicador = row.get(coluna_indicador)

    # Calcula percentil e posição no ranking para o indicador
    gdf_indicador = obter_dados_filtrados(cultura, periodo)
    gdf_indicador = gdf_indicador[gdf_indicador[coluna_indicador].notna()].copy()

    percentil = None
    posicao_ranking = None
    if valor_indicador is not None and not pd.isna(valor_indicador):
        valores = gdf_indicador[coluna_indicador].dropna().values
        if len(valores) > 0:
            # Percentil (0-100)
            percentil = float((valores <= valor_indicador).sum() / len(valores) * 100)
            # Posição no ranking (1 = maior)
            ordenados = gdf_indicador.sort_values(coluna_indicador, ascending=False)
            posicao = ordenados[ordenados[Cfg.COLUNA_MUNICIPIO_ID] == municipio_id].index
            if len(posicao) > 0:
                posicao_ranking = int(ordenados.index.get_loc(posicao[0])) + 1

    valor_mil_reais = row.get(Cfg.COLUNA_VALOR_MIL_REAIS)
    valor_reais = float(valor_mil_reais) * 1000 if valor_mil_reais is not None and not pd.isna(valor_mil_reais) else None

    return MunicipalityDetail(
        municipio_id=row[Cfg.COLUNA_MUNICIPIO_ID],
        municipio_nome=row[Cfg.COLUNA_MUNICIPIO_NOME],
        uf=row[Cfg.COLUNA_UF],
        cultura=cultura if cultura != "Todos" else row[Cfg.COLUNA_PRODUTO_NOME],
        periodo=row[Cfg.COLUNA_PERIODO],
        area_plantada_ha=row.get(Cfg.COLUNA_AREA) if pd.notna(row.get(Cfg.COLUNA_AREA)) else None,
        quantidade_produzida_t=row.get(Cfg.COLUNA_PRODUCAO) if pd.notna(row.get(Cfg.COLUNA_PRODUCAO)) else None,
        rendimento_medio_kg_ha=row.get(Cfg.COLUNA_PRODUTIVIDADE) if pd.notna(row.get(Cfg.COLUNA_PRODUTIVIDADE)) else None,
        valor_producao_mil_reais=row.get(Cfg.COLUNA_VALOR_MIL_REAIS) if pd.notna(row.get(Cfg.COLUNA_VALOR_MIL_REAIS)) else None,
        valor_producao_reais=valor_reais,
        area_km2=row.get(Cfg.COLUNA_AREA_KM2) if pd.notna(row.get(Cfg.COLUNA_AREA_KM2)) else None,
        tem_dado_agricola=valor_indicador is not None and not pd.isna(valor_indicador),
        percentil_indicador=percentil,
        posicao_ranking=posicao_ranking,
        indicador=indicador,
    )


def obter_ranking(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
    limite: int = 10,
) -> list:
    """Retorna ranking Top N por indicador."""
    gdf = obter_dados_filtrados(cultura, periodo)
    coluna_indicador = DatasetConfig.INDICADORES[indicador]

    # Remove nulos do indicador
    gdf = gdf[gdf[coluna_indicador].notna()].copy()

    # Ordena decrescente
    gdf = gdf.sort_values(coluna_indicador, ascending=False).head(limite)

    ranking = []
    for pos, (_, row) in enumerate(gdf.iterrows(), 1):
        ranking.append({
            "posicao": pos,
            "municipio_id": row[Cfg.COLUNA_MUNICIPIO_ID],
            "municipio_nome": row[Cfg.COLUNA_MUNICIPIO_NOME],
            "uf": row[Cfg.COLUNA_UF],
            "valor": float(row[coluna_indicador]),
            "cultura": cultura if cultura != "Todos" else row[Cfg.COLUNA_PRODUTO_NOME],
            "indicador": indicador,
        })
    return ranking


def obter_kpis(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
) -> dict:
    """Calcula KPIs agregados para o filtro."""
    gdf = obter_dados_filtrados(cultura, periodo)

    coluna_indicador = DatasetConfig.INDICADORES[indicador]

    # Municípios com dado para o indicador
    gdf_valido = gdf[gdf[coluna_indicador].notna()].copy()
    municipios_com_dado = gdf_valido[Cfg.COLUNA_MUNICIPIO_ID].nunique()

    # Totais
    area_total = float(gdf_valido[Cfg.COLUNA_AREA].sum()) if Cfg.COLUNA_AREA in gdf_valido else 0.0
    producao_total = float(gdf_valido[Cfg.COLUNA_PRODUCAO].sum()) if Cfg.COLUNA_PRODUCAO in gdf_valido else 0.0
    valor_total_mil_reais = float(gdf_valido[Cfg.COLUNA_VALOR_MIL_REAIS].sum()) if Cfg.COLUNA_VALOR_MIL_REAIS in gdf_valido else 0.0

    # Produtividade ponderada = soma(produção) / soma(área)
    produtividade_ponderada = None
    if area_total > 0 and producao_total > 0:
        # producao em toneladas, area em hectares -> kg/ha
        produtividade_ponderada = (producao_total * 1000) / area_total

    return {
        "area_total_ha": area_total,
        "producao_total_t": producao_total,
        "produtividade_ponderada_kg_ha": produtividade_ponderada,
        "valor_total_producao_reais": valor_total_mil_reais * 1000,
        "valor_total_producao_mil_reais": valor_total_mil_reais,
        "municipios_com_dado": int(municipios_com_dado),
        "cultura_filtro": cultura,
        "indicador_filtro": indicador,
        "periodo": periodo,
    }


def obter_scatter_data(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
) -> list[ScatterPoint]:
    """Retorna dados para gráfico Área × Produtividade."""
    gdf = obter_dados_filtrados(cultura, periodo)

    # Remove linhas sem área ou produtividade
    gdf = gdf[
        gdf[Cfg.COLUNA_AREA].notna()
        & gdf[Cfg.COLUNA_PRODUTIVIDADE].notna()
        & (gdf[Cfg.COLUNA_AREA] > 0)
        & (gdf[Cfg.COLUNA_PRODUTIVIDADE] > 0)
    ].copy()

    scatter = []
    for _, row in gdf.iterrows():
        scatter.append(ScatterPoint(
            municipio_id=row[Cfg.COLUNA_MUNICIPIO_ID],
            municipio_nome=row[Cfg.COLUNA_MUNICIPIO_NOME],
            uf=row[Cfg.COLUNA_UF],
            area_plantada_ha=float(row[Cfg.COLUNA_AREA]),
            rendimento_medio_kg_ha=float(row[Cfg.COLUNA_PRODUTIVIDADE]),
            cultura=cultura if cultura != "Todos" else row[Cfg.COLUNA_PRODUTO_NOME],
        ))
    return scatter


def _gerar_geojson_sem_cache(
    cultura: CropFilter,
    periodo: str,
    indicador: IndicatorName,
) -> dict:
    """Gera FeatureCollection GeoJSON para o mapa (EPSG:4326) — sem cache.

    Usa __geo_interface__ do GeoPandas (rápido - evita serialização string).
    """
    gdf = obter_dados_para_mapa(cultura, periodo, indicador)
    coluna_indicador = DatasetConfig.INDICADORES[indicador]

    # Prepara GeoDataFrame para serialização
    # Cria coluna "valor" com o indicador selecionado
    gdf_export = gdf.copy()
    gdf_export["valor"] = gdf_export[coluna_indicador].astype(float).where(
        gdf_export[coluna_indicador].notna(), None
    )

    # Cultura para o mapa
    if cultura == "Todos":
        gdf_export["cultura"] = "Soja e Milho"
    else:
        gdf_export["cultura"] = gdf_export[Cfg.COLUNA_PRODUTO_NOME]

    # Seleciona apenas as colunas necessárias para o GeoJSON
    cols_export = [
        Cfg.COLUNA_MUNICIPIO_ID,
        Cfg.COLUNA_MUNICIPIO_NOME,
        Cfg.COLUNA_UF,
        "valor",
        "cultura",
        "geometry",
    ]
    gdf_export = gdf_export[cols_export].copy()

    # Usa __geo_interface__ do GeoPandas (rápido - evita serialização string)
    geojson = gdf_export.__geo_interface__

    # Adiciona metadados
    geojson["indicador"] = indicador
    geojson["cultura"] = cultura
    geojson["periodo"] = periodo
    geojson["crs"] = {"type": "name", "properties": {"name": "EPSG:4326"}}

    return geojson


def obter_geojson_mapa(
    cultura: CropFilter = "Todos",
    periodo: str = "2023",
    indicador: IndicatorName = "Produção",
) -> dict:
    """Gera FeatureCollection GeoJSON para o mapa (EPSG:4326) — com cache em memória.

    Cache key: (dataset_hash, cultura, periodo, indicador).
    Armazena o dict GeoJSON já construído (evita reconstrução e serialização).
    """
    chave = _obter_chave_cache(cultura, periodo, indicador)

    cached = _geojson_cache.get(chave)
    if cached is not None:
        return cached

    geojson = _gerar_geojson_sem_cache(cultura, periodo, indicador)
    _geojson_cache.set(chave, geojson)
    return geojson


def limpar_cache() -> None:
    """Limpa cache de datasets (útil para testes)."""
    _carregar_pam_integrado.cache_clear()
    _carregar_malha_territorial.cache_clear()
    limpar_cache_geojson()