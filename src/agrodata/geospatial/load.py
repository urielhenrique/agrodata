"""Persistência de GeoParquet para a Malha Municipal IBGE."""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

logger = logging.getLogger(__name__)


CAMINHO_MALHA_PROCESSADA = Path("data/processed/ibge/malha_municipal/mg_municipios_2023.parquet")


def _verificar_pre_condicoes(gdf: gpd.GeoDataFrame) -> None:
    """Verifica pré-condições mínimas antes de salvar.

    Args:
        gdf: GeoDataFrame a ser salvo.

    Raises:
        TypeError: Se o objeto não for GeoDataFrame.
        ValueError: Se geometry ou CRS estiverem ausentes.
    """
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise TypeError(f"Esperado GeoDataFrame, recebido {type(gdf).__name__}")

    if "geometry" not in gdf.columns:
        raise ValueError("Coluna 'geometry' ausente no GeoDataFrame")

    if gdf.crs is None:
        raise ValueError("CRS nao definido no GeoDataFrame")


def salvar_malha_geoparquet(
    gdf: gpd.GeoDataFrame,
    caminho: Path | str | None = None,
) -> Path:
    """Salva a malha municipal normalizada em GeoParquet.

    Utiliza pyogrio como engine para preservar geometry e CRS.

    Args:
        gdf: GeoDataFrame normalizado da malha municipal.
        caminho: Caminho de saída. Se None, usa o caminho padrão do projeto.

    Returns:
        Caminho absoluto do arquivo salvo.

    Raises:
        TypeError: Se gdf não for GeoDataFrame.
        ValueError: Se geometry ou CRS estiverem ausentes.
    """
    _verificar_pre_condicoes(gdf)

    if caminho is None:
        caminho = CAMINHO_MALHA_PROCESSADA

    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_parquet(caminho, engine="pyarrow", index=False)

    logger.info("Malha municipal salva em GeoParquet: %s (%d feicoes)", caminho, len(gdf))

    return caminho.resolve()


def carregar_malha_geoparquet(caminho: Path | str | None = None) -> gpd.GeoDataFrame:
    """Carrega a malha municipal a partir de um GeoParquet.

    Args:
        caminho: Caminho do arquivo GeoParquet. Se None, usa o caminho padrao.

    Returns:
        GeoDataFrame com a malha municipal.
    """
    if caminho is None:
        caminho = CAMINHO_MALHA_PROCESSADA

    caminho = Path(caminho)

    gdf = gpd.read_parquet(caminho)

    logger.info("Malha municipal carregada de GeoParquet: %s (%d feicoes)", caminho, len(gdf))

    return gdf