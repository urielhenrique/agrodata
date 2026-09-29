"""Ingestão da Malha Municipal IBGE 2023 de Minas Gerais."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import geopandas as gpd

logger = logging.getLogger(__name__)

# Caminho relativo ao diretório raiz do projeto
MALHA_ZIP_PATH = Path("data/raw/ibge/malha_municipal/2023/MG_Municipios_2023.zip")
MALHA_SHP_NAME = "MG_Municipios_2023.shp"

# Número esperado de feições para Minas Gerais
NUM_MUNICIPIOS_ESPERADO = 853
# Código IBGE de Minas Gerais
UF_MG = "MG"


def _extrair_shapefile(zip_path: Path, tmp_dir: Path) -> Path:
    """Extrai o arquivo shapefile do ZIP para um diretório temporário.

    Args:
        zip_path: Caminho para o arquivo ZIP.
        tmp_dir: Diretório temporário de extração.

    Returns:
        Caminho para o arquivo shapefile extraído.
    """
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp_dir)
    return tmp_dir / MALHA_SHP_NAME


def ler_malha_municipal(
    zip_path: Path | None = None,
    raiz: Path | None = None,
) -> gpd.GeoDataFrame:
    """Lê a Malha Municipal IBGE 2023 de Minas Gerais.

    Utiliza GeoPandas com engine pyogrio para ler o shapefile
    extraído do ZIP original.

    Args:
        zip_path: Caminho para o arquivo ZIP da malha.
            Se None, usa o caminho padrão do projeto.
        raiz: Diretório raiz do projeto. Auto-detecta se None.

    Returns:
        GeoDataFrame com as feições originais da malha.

    Raises:
        FileNotFoundError: Se o arquivo ZIP não for encontrado.
    """
    if zip_path is None:
        if raiz is not None:
            zip_path = raiz / "data" / "raw" / "ibge" / "malha_municipal" / "2023" / "MG_Municipios_2023.zip"
        else:
            zip_path = MALHA_ZIP_PATH

    if not zip_path.exists():
        raise FileNotFoundError(f"Arquivo ZIP da malha não encontrado: {zip_path}")

    logger.info("Lendo malha municipal de: %s", zip_path)

    import tempfile

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        shp_path = _extrair_shapefile(zip_path, tmp_dir)
        gdf = gpd.read_file(shp_path, engine="pyogrio")
        logger.info("Malha lida com sucesso: %d feições", len(gdf))
        return gdf
    finally:
        import shutil
        shutil.rmtree(tmp_dir)
