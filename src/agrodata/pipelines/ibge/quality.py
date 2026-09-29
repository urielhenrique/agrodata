"""Verificações de qualidade de dados para o dataset agrícola IBGE."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from agrodata.pipelines.ibge.load import COLUNAS_ORDEM
from agrodata.pipelines.ibge.schemas import VALORES_AUSENTES

# ---------------------------------------------------------------------------
# Chave lógica para identificação de duplicidade
# ---------------------------------------------------------------------------

# Chave lógica: (variavel_id, classificacao_id, categoria_codigo,
#                localidade_id, periodo)
#
# Justificativa:
# - variavel_id: qual variável está sendo medida (ex: área plantada, produção)
# - classificacao_id + categoria_codigo: qual produto/categoria dentro da variável
# - localidade_id: em qual município/UF/Brasil
# - periodo: em qual ano/semestre/trimestre
#
# Esses campos juntos identificam exclusivamente uma observação:
# para uma dada variável, classificação, categoria, localidade e período,
# a API SIDRA retorna exatamente um valor.
#
# Campos excluídos da chave:
# - variavel_nome, variavel_unidade: derivados de variavel_id (dependência funcional)
# - classificacao_nome: derivado de classificacao_id
# - categoria_nome: derivado de categoria_codigo
# - localidade_nome, nivel_territorial_id, nivel_territorial_nome:
#   derivados de localidade_id
# - valor_bruto, valor_numerico: são o valor medido, não parte da identidade

CHAVE_LOGICA: list[str] = [
    "variavel_id",
    "classificacao_id",
    "categoria_codigo",
    "localidade_id",
    "periodo",
]


# ---------------------------------------------------------------------------
# Colunas obrigatórias (não devem ter nulos)
# ---------------------------------------------------------------------------

COLUNAS_OBRIGATORIAS: list[str] = [
    "variavel_id",
    "variavel_nome",
    "classificacao_id",
    "categoria_codigo",
    "localidade_id",
    "periodo",
    "valor_bruto",
]


# ---------------------------------------------------------------------------
# Resultados das verificações
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoSchema:
    """Resultado da verificação de schema."""

    colunas_esperadas: list[str]
    colunas_encontradas: list[str]
    colunas_ausentes: list[str]
    colunas_extras: list[str]
    valido: bool


@dataclass(frozen=True)
class ResultadoNulos:
    """Resultado da verificação de valores nulos."""

    colunas_verificadas: list[str]
    nulos_por_coluna: dict[str, int]
    total_nulos: int
    valido: bool


@dataclass(frozen=True)
class ResultadoValoresNumericos:
    """Resultado da verificação de valores numéricos."""

    total_registros: int
    com_valor: int
    sem_valor: int


@dataclass(frozen=True)
class ResultadoValoresEspeciais:
    """Resultado da contagem de valores especiais."""

    contagem: dict[str, int]
    total: int


@dataclass(frozen=True)
class ResultadoDuplicidade:
    """Resultado da verificação de duplicidade."""

    chave: list[str]
    total_linhas: int
    linhas_unicas: int
    duplicatas: int
    valido: bool


@dataclass(frozen=True)
class ResultadoPerfil:
    """Perfil descritivo do dataset."""

    num_linhas: int
    num_colunas: int
    variaveis: list[str]
    produtos: list[str]
    localidades: list[str]
    periodos: list[str]
    unidades: list[str]
    nulos_por_coluna: dict[str, int]
    duplicatas: int


# ---------------------------------------------------------------------------
# Funções de verificação
# ---------------------------------------------------------------------------


def verificar_schema(dataframe: pd.DataFrame) -> ResultadoSchema:
    """Verifica se o DataFrame contém exatamente as colunas esperadas.

    Args:
        dataframe: DataFrame a ser verificado.

    Returns:
        ResultadoSchema com detalhes da verificação.
    """
    colunas_df = list(dataframe.columns)
    colunas_esperadas = set(COLUNAS_ORDEM)
    colunas_encontradas = set(colunas_df)

    ausentes = sorted(colunas_esperadas - colunas_encontradas)
    extras = sorted(colunas_encontradas - colunas_esperadas)

    return ResultadoSchema(
        colunas_esperadas=COLUNAS_ORDEM,
        colunas_encontradas=colunas_df,
        colunas_ausentes=ausentes,
        colunas_extras=extras,
        valido=len(ausentes) == 0 and len(extras) == 0,
    )


def verificar_nulos(dataframe: pd.DataFrame) -> ResultadoNulos:
    """Verifica valores nulos nas colunas obrigatórias.

    Args:
        dataframe: DataFrame a ser verificado.

    Returns:
        ResultadoNulos com contagem de nulos por coluna.
    """
    nulos = {}
    for col in COLUNAS_OBRIGATORIAS:
        if col in dataframe.columns:
            nulos[col] = int(dataframe[col].isna().sum())
        else:
            nulos[col] = len(dataframe)

    total = sum(nulos.values())

    return ResultadoNulos(
        colunas_verificadas=COLUNAS_OBRIGATORIAS,
        nulos_por_coluna=nulos,
        total_nulos=total,
        valido=total == 0,
    )


def contar_valores_numericos(dataframe: pd.DataFrame) -> ResultadoValoresNumericos:
    """Conta registros com e sem valor_numerico válido.

    Args:
        dataframe: DataFrame a ser verificado.

    Returns:
        ResultadoValoresNumericos com contagens.
    """
    if "valor_numerico" not in dataframe.columns:
        return ResultadoValoresNumericos(
            total_registros=len(dataframe),
            com_valor=0,
            sem_valor=len(dataframe),
        )

    total = len(dataframe)
    com_valor = int(dataframe["valor_numerico"].notna().sum())
    sem_valor = total - com_valor

    return ResultadoValoresNumericos(
        total_registros=total,
        com_valor=com_valor,
        sem_valor=sem_valor,
    )


def contar_valores_especiais(dataframe: pd.DataFrame) -> ResultadoValoresEspeciais:
    """Conta ocorrências de valores especiais em valor_bruto.

    Valores especiais ("-", "..", "...") representam dados ausentes
    ou inibidos pela fonte (IBGE) e não devem ser convertidos em zero.

    Args:
        dataframe: DataFrame a ser verificado.

    Returns:
        ResultadoValoresEspeciais com contagem por valor.
    """
    contagem: dict[str, int] = {}

    if "valor_bruto" not in dataframe.columns:
        return ResultadoValoresEspeciais(contagem=contagem, total=0)

    for valor in VALORES_AUSENTES:
        count = int((dataframe["valor_bruto"] == valor).sum())
        if count > 0:
            contagem[valor] = count

    total = sum(contagem.values())

    return ResultadoValoresEspeciais(contagem=contagem, total=total)


def verificar_duplicidade(dataframe: pd.DataFrame) -> ResultadoDuplicidade:
    """Verifica duplicidade usando a chave lógica do dataset.

    A chave lógica (variavel_id, classificacao_id, categoria_codigo,
    localidade_id, periodo) identifica exclusivamente uma observação
    na API SIDRA. Registros duplicados indicam erro na transformação.

    Args:
        dataframe: DataFrame a ser verificado.

    Returns:
        ResultadoDuplicidade com contagens.
    """
    colunas_presentes = [c for c in CHAVE_LOGICA if c in dataframe.columns]

    total = len(dataframe)

    if not colunas_presentes or total == 0:
        return ResultadoDuplicidade(
            chave=CHAVE_LOGICA,
            total_linhas=total,
            linhas_unicas=total,
            duplicatas=0,
            valido=True,
        )

    unicas = len(dataframe.drop_duplicates(subset=colunas_presentes))
    duplicatas = total - unicas

    return ResultadoDuplicidade(
        chave=CHAVE_LOGICA,
        total_linhas=total,
        linhas_unicas=unicas,
        duplicatas=duplicatas,
        valido=duplicatas == 0,
    )


def gerar_perfil(dataframe: pd.DataFrame) -> ResultadoPerfil:
    """Gera perfil descritivo básico do dataset.

    Args:
        dataframe: DataFrame a ser perfilado.

    Returns:
        ResultadoPerfil com informações descritivas.
    """
    nulos = {}
    for col in dataframe.columns:
        nulos[col] = int(dataframe[col].isna().sum())

    duplicatas = verificar_duplicidade(dataframe).duplicatas

    def _valores_unicos(col: str) -> list[str]:
        if col in dataframe.columns:
            return sorted(dataframe[col].dropna().unique().tolist())
        return []

    return ResultadoPerfil(
        num_linhas=len(dataframe),
        num_colunas=len(dataframe.columns),
        variaveis=_valores_unicos("variavel_nome"),
        produtos=_valores_unicos("categoria_nome"),
        localidades=_valores_unicos("localidade_nome"),
        periodos=_valores_unicos("periodo"),
        unidades=_valores_unicos("variavel_unidade"),
        nulos_por_coluna=nulos,
        duplicatas=duplicatas,
    )
