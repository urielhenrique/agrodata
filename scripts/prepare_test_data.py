"""Prepara datasets sintéticos determinísticos para testes/CI.

Uso:
    python scripts/prepare_test_data.py

Gera (sem internet) os GeoParquets esperados por ``DatasetConfig`` a partir
do gerador versionado em ``tests/_mg_sintetico.py``. Os arquivos ficam em
``data/processed/`` (ignorado pelo Git) e nunca são versionados.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from _mg_sintetico import garantir_datasets_teste

from agrodata.config import DatasetConfig


def main() -> None:
    garantir_datasets_teste()
    print(f"Malha: {DatasetConfig.MALHA_TERRITORIAL}")
    print(f"PAM integrado: {DatasetConfig.PAM_INTEGRADO}")


if __name__ == "__main__":
    main()
