"""Isola os testes de analytics nos datasets sintéticos determinísticos.

Os testes sempre usam parquets sintéticos gerados em diretório temporário,
independentemente de existirem datasets reais em ``data/processed/``.
Nenhum arquivo real é sobrescrito ou apagado.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _datasets_mg_isolados(tmp_path_factory: pytest.TempPathFactory):
    from _mg_sintetico import salvar_datasets

    from agrodata.analytics.queries import limpar_cache
    from agrodata.config import DatasetConfig

    base = tmp_path_factory.mktemp("agrodata_mg_test")
    caminho_malha = base / "mg_municipios_2023.parquet"
    caminho_pam = base / "mg_pam_2023_soja_milho.parquet"
    salvar_datasets(caminho_malha, caminho_pam)

    pam_original = DatasetConfig.PAM_INTEGRADO
    malha_original = DatasetConfig.MALHA_TERRITORIAL
    DatasetConfig.PAM_INTEGRADO = caminho_pam  # type: ignore[assignment]
    DatasetConfig.MALHA_TERRITORIAL = caminho_malha  # type: ignore[assignment]
    limpar_cache()
    yield
    DatasetConfig.PAM_INTEGRADO = pam_original  # type: ignore[assignment]
    DatasetConfig.MALHA_TERRITORIAL = malha_original  # type: ignore[assignment]
    limpar_cache()
