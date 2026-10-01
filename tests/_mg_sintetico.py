"""Datasets sintéticos determinísticos para testes (MVP1/MG).

Gera os dois GeoParquets esperados por ``DatasetConfig`` sem internet:

- ``mg_municipios_2023.parquet`` (malha, 853 linhas)
- ``mg_pam_2023_soja_milho.parquet`` (PAM integrado, 1137 linhas)

Propriedades preservadas em relação ao dataset real:

- 847 municípios com PAM (Milho em todos, Soja em 290) + 6 só na malha
- 1137 observações (847 Milho + 290 Soja)
- município ``3100104`` = "Abadia dos Dourados" com dado válido
- ``9999999`` não existe em nenhum dataset
- todos os valores agrícolas > 0 e sem nulos
- CRS EPSG:4674, geometrias válidas
- agregação "Todos" resulta em 847 features (uma por município)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import box

from agrodata.config import DatasetConfig

SEED = 42
N_PAM_MUNICIPIOS = 847
N_MALHA_EXTRA = 6
N_SOJA = 290
MUNICIPIO_REFERENCIA_ID = "3100104"
MUNICIPIO_REFERENCIA_NOME = "Abadia dos Dourados"


def _gerar_ids_pam() -> list[str]:
    """Gera 847 IDs de município incluindo o de referência."""
    base = 3100104
    return [str(base + i) for i in range(N_PAM_MUNICIPIOS)]


def _geometria_grade(indice: int) -> object:
    """Gera um quadrado válido determinístico dentro do bbox de MG."""
    lon = -51.0 + (indice % 30) * 0.4
    lat = -23.0 + (indice // 30) * 0.3
    return box(lon, lat, lon + 0.05, lat + 0.05)


def construir_malha(ids_pam: list[str]) -> gpd.GeoDataFrame:
    """Constrói a malha sintética (853 linhas)."""
    ids_extras = [f"319990{i}" for i in range(1, N_MALHA_EXTRA + 1)]
    todos_ids = ids_pam + ids_extras
    nomes = [
        MUNICIPIO_REFERENCIA_NOME if mid == MUNICIPIO_REFERENCIA_ID else f"Município {mid}"
        for mid in todos_ids
    ]
    rng = np.random.default_rng(SEED)
    areas = rng.uniform(100.0, 2000.0, size=len(todos_ids)).round(2)
    geometrias = [_geometria_grade(i) for i in range(len(todos_ids))]
    gdf = gpd.GeoDataFrame(
        {
            "municipio_id": todos_ids,
            "municipio_nome": nomes,
            "cd_uf": ["31"] * len(todos_ids),
            "uf": ["MG"] * len(todos_ids),
            "area_km2": areas,
            "geometry": geometrias,
        },
        crs="EPSG:4674",
    )
    for coluna in ["municipio_id", "municipio_nome", "cd_uf"]:
        gdf[coluna] = gdf[coluna].astype("string")
    return gdf


def construir_pam_integrado(malha: gpd.GeoDataFrame, ids_pam: list[str]) -> gpd.GeoDataFrame:
    """Constrói o PAM integrado sintético (1137 linhas)."""
    rng = np.random.default_rng(SEED)
    geo_por_id = {row.municipio_id: row.geometry for row in malha.itertuples()}
    area_por_id = {row.municipio_id: float(row.area_km2) for row in malha.itertuples()}
    nome_por_id = {row.municipio_id: str(row.municipio_nome) for row in malha.itertuples()}

    ids_soja = set(ids_pam[:N_SOJA])
    # Garante que a referência tenha Soja e Milho.
    ids_soja.add(MUNICIPIO_REFERENCIA_ID)

    linhas: list[dict] = []
    for mid in ids_pam:
        produtos = [("40122", "Milho (em grão)")]
        if mid in ids_soja:
            produtos.append(("40124", "Soja (em grão)"))
        for codigo, nome in produtos:
            area = round(float(rng.uniform(100.0, 20000.0)), 2)
            rendimento = round(float(rng.uniform(2000.0, 6000.0)), 2)
            producao = round(area * rendimento / 1000.0, 2)
            preco = float(rng.uniform(1.5, 3.0))
            valor = round(producao * preco, 2)
            linhas.append(
                {
                    "municipio_id": mid,
                    "produto_codigo": codigo,
                    "produto_nome": nome,
                    "periodo": "2023",
                    "area_plantada_ha": area,
                    "quantidade_produzida_t": producao,
                    "rendimento_medio_kg_ha": rendimento,
                    "valor_producao_mil_reais": valor,
                    "municipio_nome": nome_por_id[mid],
                    "cd_uf": "31",
                    "uf": "MG",
                    "area_km2": area_por_id[mid],
                    "geometry": geo_por_id[mid],
                }
            )
    gdf = gpd.GeoDataFrame(linhas, crs="EPSG:4674")
    for coluna in ["municipio_id", "produto_codigo", "produto_nome", "periodo", "municipio_nome", "cd_uf"]:
        gdf[coluna] = gdf[coluna].astype("string")
    # Ordena para determinismo total do arquivo.
    gdf = gdf.sort_values(["municipio_id", "produto_codigo"]).reset_index(drop=True)
    return gdf


def salvar_datasets(caminho_malha: Path, caminho_pam: Path) -> None:
    """Constrói e salva os datasets sintéticos nos caminhos informados."""
    ids_pam = _gerar_ids_pam()
    malha = construir_malha(ids_pam)
    pam = construir_pam_integrado(malha, ids_pam)
    caminho_malha.parent.mkdir(parents=True, exist_ok=True)
    caminho_pam.parent.mkdir(parents=True, exist_ok=True)
    malha.to_parquet(caminho_malha, engine="pyarrow", index=False)
    pam.to_parquet(caminho_pam, engine="pyarrow", index=False)


def garantir_datasets_teste() -> None:
    """Gera os parquets de teste em ``data/processed`` se ainda não existirem.

    Não sobrescreve arquivos existentes (nunca apaga dados reais locais).
    Usado pelo script explícito ``scripts/prepare_test_data.py``.
    """
    if DatasetConfig.PAM_INTEGRADO.exists() and DatasetConfig.MALHA_TERRITORIAL.exists():
        return
    if not DatasetConfig.MALHA_TERRITORIAL.exists() or not DatasetConfig.PAM_INTEGRADO.exists():
        ids_pam = _gerar_ids_pam()
        malha = construir_malha(ids_pam)
        pam = construir_pam_integrado(malha, ids_pam)
        DatasetConfig.MALHA_TERRITORIAL.parent.mkdir(parents=True, exist_ok=True)
        DatasetConfig.PAM_INTEGRADO.parent.mkdir(parents=True, exist_ok=True)
        if not DatasetConfig.MALHA_TERRITORIAL.exists():
            malha.to_parquet(DatasetConfig.MALHA_TERRITORIAL, engine="pyarrow", index=False)
        if not DatasetConfig.PAM_INTEGRADO.exists():
            pam.to_parquet(DatasetConfig.PAM_INTEGRADO, engine="pyarrow", index=False)
