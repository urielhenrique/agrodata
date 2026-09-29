"""Camada analítica municipal — transformação de long para wide."""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Mapeamento de variáveis para colunas do dataset analítico
# ---------------------------------------------------------------------------

# O dataset long do IBGE possui a coluna variavel_id que identifica cada
# variável. No formato analítico (wide), cada variável vira uma coluna.
# O mapeamento abaixo define o nome da coluna de saída para cada variável,
# incluindo a unidade no nome para clareza.

MAPEAMENTO_VARIAVEIS: dict[str, str] = {
    "8331": "area_plantada_ha",
    "214": "quantidade_produzida_t",
    "112": "rendimento_medio_kg_ha",
    "215": "valor_producao_mil_reais",
}

# Colunas identificadoras (não sofrem pivot)
COLUNAS_IDENTIFICACAO: list[str] = [
    "localidade_id",
    "localidade_nome",
    "nivel_territorial_id",
    "nivel_territorial_nome",
    "categoria_codigo",
    "categoria_nome",
    "periodo",
]

# Ordem final das colunas no dataset analítico
COLUNAS_ANALITICAS: list[str] = [
    "municipio_id",
    "municipio_nome",
    "nivel_territorial_id",
    "nivel_territorial_nome",
    "produto_codigo",
    "produto_nome",
    "periodo",
    "area_plantada_ha",
    "quantidade_produzida_t",
    "rendimento_medio_kg_ha",
    "valor_producao_mil_reais",
]


# ---------------------------------------------------------------------------
# Funções de transformação
# ---------------------------------------------------------------------------


def transformar_long_para_wide(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Transforma o dataset long em formato analítico wide.

    Cada variável do IBGE (8331, 214, 112, 215) vira uma coluna separada.
    A identidade lógica do resultado é: produto + município + período.

    Regras:
    - Não preenche valores ausentes com zero.
    - Preserva NaN/None quando o valor numérico não existe.
    - Preserva códigos como string.
    - Preserva período como string.
    - Não recalcula rendimento médio (usa variável 112 do IBGE).

    Args:
        dataframe: DataFrame no formato long (saída do pipeline normalizado).

    Returns:
        DataFrame no formato wide com colunas definidas em COLUNAS_ANALITICAS.
    """
    if dataframe.empty:
        return pd.DataFrame(columns=COLUNAS_ANALITICAS)

    # Seleciona colunas necessárias
    colunas_necessarias = [
        "localidade_id",
        "localidade_nome",
        "nivel_territorial_id",
        "nivel_territorial_nome",
        "categoria_codigo",
        "categoria_nome",
        "periodo",
        "variavel_id",
        "valor_numerico",
    ]

    df = dataframe[colunas_necessarias].copy()

    # Pivot: cada variável vira uma coluna
    df_wide = df.pivot_table(
        index=[
            "localidade_id",
            "localidade_nome",
            "nivel_territorial_id",
            "nivel_territorial_nome",
            "categoria_codigo",
            "categoria_nome",
            "periodo",
        ],
        columns="variavel_id",
        values="valor_numerico",
        aggfunc="first",  # Deve haver exatamente 1 valor por combinação
    ).reset_index()

    # Remove nome do eixo de colunas
    df_wide.columns.name = None

    # Renomeia colunas de variáveis usando o mapeamento
    rename_map = {vid: nome for vid, nome in MAPEAMENTO_VARIAVEIS.items() if vid in df_wide.columns}
    df_wide = df_wide.rename(columns=rename_map)

    # Renomeia colunas de identificação
    df_wide = df_wide.rename(columns={
        "localidade_id": "municipio_id",
        "localidade_nome": "municipio_nome",
        "categoria_codigo": "produto_codigo",
        "categoria_nome": "produto_nome",
    })

    # Garante que todas as colunas esperadas existem
    for col in COLUNAS_ANALITICAS:
        if col not in df_wide.columns:
            df_wide[col] = pd.NA

    # Reordena colunas
    df_wide = df_wide[COLUNAS_ANALITICAS]

    # Preserva tipos: IDs e textos como string
    colunas_string = [
        "municipio_id", "municipio_nome",
        "nivel_territorial_id", "nivel_territorial_nome",
        "produto_codigo", "produto_nome", "periodo",
    ]
    for col in colunas_string:
        df_wide[col] = df_wide[col].astype("string")

    return df_wide


def verificar_unicidade(dataframe: pd.DataFrame) -> tuple[bool, int]:
    """Verifica se a combinação produto + município + período é única.

    Args:
        dataframe: DataFrame no formato wide.

    Returns:
        Tupla (eh_unico, num_duplicatas).
    """
    if dataframe.empty:
        return True, 0

    chave = ["produto_codigo", "municipio_id", "periodo"]
    total = len(dataframe)
    unicas = len(dataframe.drop_duplicates(subset=chave))
    duplicatas = total - unicas

    return duplicatas == 0, duplicatas


def contar_ausentes(dataframe: pd.DataFrame) -> dict[str, int]:
    """Conta valores ausentes por coluna de variável.

    Args:
        dataframe: DataFrame no formato wide.

    Returns:
        Dicionário com contagem de ausentes por coluna.
    """
    colunas_variaveis = [
        "area_plantada_ha",
        "quantidade_produzida_t",
        "rendimento_medio_kg_ha",
        "valor_producao_mil_reais",
    ]

    ausentes = {}
    for col in colunas_variaveis:
        if col in dataframe.columns:
            ausentes[col] = int(dataframe[col].isna().sum())
        else:
            ausentes[col] = len(dataframe)

    return ausentes
