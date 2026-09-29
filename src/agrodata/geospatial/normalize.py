"""Normalização da Malha Municipal IBGE para formato GeoDataFrame padronizado."""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)


def normalizar_malha_municipal(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Normaliza a Malha Municipal IBGE para o formato padronizado do projeto.

    Mapeamento:
    - CD_MUN → municipio_id (string, 7 dígitos)
    - NM_MUN → municipio_nome (string)
    - CD_UF → cd_uf (string)
    - uf → uf (string, derivado como "MG" pois é a malha de MG)
    - AREA_KM2 → area_km2 (float64)
    - geometry → geometry (preservado)

    Args:
        gdf: GeoDataFrame da malha municipal original.

    Returns:
        GeoDataFrame normalizado com colunas padronizadas.
    """
    logger.debug("Iniciando normalizacao da malha municipal")

    # Cria copia para nao modificar o original
    gdf_norm = gdf.copy()

    # Verifica se as colunas necessarias existem
    colunas_necessarias = ["CD_MUN", "NM_MUN", "CD_UF", "AREA_KM2", "geometry"]
    colunas_faltantes = [c for c in colunas_necessarias if c not in gdf_norm.columns]
    if colunas_faltantes:
        raise ValueError(f"Colunas faltantes para normalizacao: {colunas_faltantes}")

    # Aplica o mapeamento
    gdf_norm["municipio_id"] = gdf_norm["CD_MUN"].astype("string")
    gdf_norm["municipio_nome"] = gdf_norm["NM_MUN"].astype("string")
    gdf_norm["cd_uf"] = gdf_norm["CD_UF"].astype("string")
    # uf é derivado explicitamente do contexto da ingestão (malha de MG)
    gdf_norm["uf"] = "MG"
    gdf_norm["area_km2"] = pd.to_numeric(gdf_norm["AREA_KM2"], errors="coerce").astype("float64")
    # geometry é preservado como está

    # Seleciona apenas as colunas padronizadas (na ordem definida)
    colunas_padrao = [
        "municipio_id",
        "municipio_nome",
        "cd_uf",
        "uf",
        "area_km2",
        "geometry",
    ]

    gdf_resultado = gdf_norm[colunas_padrao].copy()

    # Verifica integridade da normalizacao
    if len(gdf_resultado) != len(gdf):
        raise RuntimeError(
            f"Normalizacao alterou o numero de linhas: {len(gdf)} -> {len(gdf_resultado)}"
        )

    # Verifica municipio_id é string de 7 digitos
    municipio_id_tamanho = gdf_resultado["municipio_id"].str.len()
    if not (municipio_id_tamanho == 7).all():
        invalidos = gdf_resultado[municipio_id_tamanho != 7]["municipio_id"].tolist()
        raise RuntimeError(
            f"municipio_id possui valores com tamanho != 7: {invalidos}"
        )

    logger.debug(
        "Normalizacao concluida: %d linhas, colunas=%s",
        len(gdf_resultado),
        list(gdf_resultado.columns),
    )

    return gdf_resultado