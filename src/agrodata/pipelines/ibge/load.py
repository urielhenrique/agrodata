"""Persistência analítica de dados IBGE em formato Parquet."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from agrodata.pipelines.ibge.schemas import RegistroAgricola

# Colunas do dataset e seus tipos desejados.
# IDs e textos permanecem como string; valores numéricos permitem None.
COLUNAS_DATASET: dict[str, str] = {
    "variavel_id": "string",
    "variavel_nome": "string",
    "variavel_unidade": "string",
    "classificacao_id": "string",
    "classificacao_nome": "string",
    "categoria_codigo": "string",
    "categoria_nome": "string",
    "localidade_id": "string",
    "localidade_nome": "string",
    "nivel_territorial_id": "string",
    "nivel_territorial_nome": "string",
    "periodo": "string",
    "valor_bruto": "string",
    "valor_numerico": "float64",
}

COLUNAS_ORDEM = list(COLUNAS_DATASET.keys())


def registros_para_dataframe(registros: list[RegistroAgricola]) -> pd.DataFrame:
    """Converte uma lista de RegistroAgricola em um DataFrame pandas.

    Controla explicitamente os tipos de cada coluna:
    - IDs e campos de texto: string (preserva códigos como "5103403")
    - periodo: string (preserve formato original, ex: "2023")
    - valor_bruto: string (preserva valores como "-", "..", "...")
    - valor_numerico: float64 (permite NaN para valores ausentes)

    Args:
        registros: Lista de registros agrícolas transformados.

    Returns:
        DataFrame com colunas na ordem definida por COLUNAS_ORDEM.
    """
    if not registros:
        return pd.DataFrame(columns=COLUNAS_ORDEM)

    dados = [r.model_dump() for r in registros]
    df = pd.DataFrame(dados)

    # Reordena colunas e aplica tipos explicitamente
    df = df[COLUNAS_ORDEM]

    # Aplica dtype de string para colunas de texto/ID
    colunas_string = [c for c, t in COLUNAS_DATASET.items() if t == "string"]
    for col in colunas_string:
        df[col] = df[col].astype("string")

    # valor_numerico já vem como float ou None do Pydantic
    # None vira NaN automaticamente no pandas, o que é correto
    df["valor_numerico"] = df["valor_numerico"].astype("float64")

    return df


def salvar_parquet(
    dataframe: pd.DataFrame,
    caminho: Path | str,
) -> Path:
    """Salva um DataFrame em formato Parquet.

    Cria os diretórios intermediários automaticamente se necessário.

    Args:
        dataframe: DataFrame a ser salvo.
        caminho: Caminho do arquivo de saída (terminando em .parquet).

    Returns:
        Caminho absoluto do arquivo salvo.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    dataframe.to_parquet(
        caminho,
        engine="pyarrow",
        index=False,
    )

    return caminho.resolve()


def carregar_parquet(caminho: Path | str) -> pd.DataFrame:
    """Carrega um DataFrame a partir de um arquivo Parquet.

    Args:
        caminho: Caminho do arquivo Parquet.

    Returns:
        DataFrame com os dados carregados e tipos preservados.
    """
    return pd.read_parquet(caminho, engine="pyarrow")
