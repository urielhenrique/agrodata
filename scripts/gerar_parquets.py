"""Script para gerar Parquets a partir dos JSONs RAW existentes.

Executar com:
    python -m scripts.gerar_parquets

Ou diretamente:
    python scripts/gerar_parquets.py
"""

from __future__ import annotations

import json
from pathlib import Path

from agrodata.pipelines.ibge.load import carregar_parquet, registros_para_dataframe, salvar_parquet
from agrodata.pipelines.ibge.transform import transformar_resposta_pam

# Diretórios base
RAW_DIR = Path("data/raw/ibge/pam")
PROCESSED_DIR = Path("data/processed/ibge/pam")

# Arquivos de entrada e saída
ARQUIVOS = [
    ("pam_5457_2023_amostra.json", "pam_5457_2023_amostra.parquet"),
    ("pam_5457_2023_sp_soja.json", "pam_5457_2023_sp_soja.parquet"),
]


def gerar_parquets() -> None:
    """Gera arquivos Parquet a partir dos JSONs RAW."""
    for arquivo_json, arquivo_parquet in ARQUIVOS:
        caminho_json = RAW_DIR / arquivo_json
        caminho_parquet = PROCESSED_DIR / arquivo_parquet

        print(f"Processando: {caminho_json}")

        # Carrega JSON
        with open(caminho_json, encoding="utf-8") as f:
            dados = json.load(f)

        # Transforma em registros
        registros = transformar_resposta_pam(dados)
        print(f"  Registros transformados: {len(registros)}")

        # Converte para DataFrame
        df = registros_para_dataframe(registros)
        print(f"  DataFrame shape: {df.shape}")
        print(f"  Colunas: {list(df.columns)}")

        # Salva Parquet
        caminho_salvo = salvar_parquet(df, caminho_parquet)
        print(f"  Parquet salvo em: {caminho_salvo}")

        # Verifica leitura
        df_verificacao = carregar_parquet(caminho_salvo)
        assert df_verificacao.shape == df.shape, "Erro na verificação!"
        print(f"  Verificação OK: {df_verificacao.shape[0]} linhas, {df_verificacao.shape[1]} colunas")
        print()


if __name__ == "__main__":
    gerar_parquets()
    print("Geração de Parquets concluída!")
