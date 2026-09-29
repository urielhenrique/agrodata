"""Análise exploratória descritiva do dataset agrícola IBGE."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# ---------------------------------------------------------------------------
# Resultados da análise
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EstatisticasVariavel:
    """Estatísticas descritivas para uma combinação produto × variável."""

    variavel_id: str
    variavel_nome: str
    variavel_unidade: str
    categoria_codigo: str
    categoria_nome: str
    total_registros: int
    registros_validos: int
    registros_ausentes: int
    minimo: float | None
    maximo: float | None
    media: float | None
    mediana: float | None


@dataclass(frozen=True)
class RegistroRanking:
    """Um registro no ranking de municípios."""

    localidade_id: str
    localidade_nome: str
    valor_numerico: float


@dataclass(frozen=True)
class ResultadoRanking:
    """Resultado do ranking de municípios para uma combinação produto × variável."""

    variavel_id: str
    variavel_nome: str
    variavel_unidade: str
    categoria_codigo: str
    categoria_nome: str
    maiores: list[RegistroRanking]
    menores: list[RegistroRanking]


@dataclass(frozen=True)
class ResumoUnidades:
    """Verificação de unidades por variável."""

    variavel_id: str
    variavel_nome: str
    unidades_encontradas: list[str]
    consistente: bool


@dataclass(frozen=True)
class ResumoGeral:
    """Resumo geral do dataset."""

    num_linhas: int
    num_colunas: int
    variaveis: list[dict[str, str]]
    produtos: list[dict[str, str]]
    num_municipios: int
    num_periodos: list[str]
    unidades_por_variavel: list[ResumoUnidades]
    estatisticas: list[EstatisticasVariavel]
    rankings: list[ResultadoRanking]
    duplicidades: int


# ---------------------------------------------------------------------------
# Funções de análise
# ---------------------------------------------------------------------------


def listar_variaveis(dataframe: pd.DataFrame) -> list[dict[str, str]]:
    """Lista todas as variáveis existentes no dataset.

    Args:
        dataframe: DataFrame a ser analisado.

    Returns:
        Lista de dicionários com id, nome e unidade de cada variável.
    """
    if dataframe.empty:
        return []

    variaveis = (
        dataframe[["variavel_id", "variavel_nome", "variavel_unidade"]]
        .drop_duplicates()
        .sort_values("variavel_id")
    )

    return [
        {
            "id": str(row["variavel_id"]),
            "nome": str(row["variavel_nome"]),
            "unidade": str(row["variavel_unidade"]),
        }
        for _, row in variaveis.iterrows()
    ]


def listar_produtos(dataframe: pd.DataFrame) -> list[dict[str, str]]:
    """Lista todos os produtos/categorias existentes no dataset.

    Args:
        dataframe: DataFrame a ser analisado.

    Returns:
        Lista de dicionários com código e nome de cada produto.
    """
    if dataframe.empty:
        return []

    produtos = (
        dataframe[["categoria_codigo", "categoria_nome"]]
        .drop_duplicates()
        .sort_values("categoria_codigo")
    )

    return [
        {
            "codigo": str(row["categoria_codigo"]),
            "nome": str(row["categoria_nome"]),
        }
        for _, row in produtos.iterrows()
    ]


def contar_municipios_por_produto_variavel(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Conta municípios com dados numéricos para cada combinação produto × variável.

    Args:
        dataframe: DataFrame a ser analisado.

    Returns:
        DataFrame com contagem de municípios por combinação.
    """
    if dataframe.empty:
        return pd.DataFrame(
            columns=[
                "variavel_id",
                "variavel_nome",
                "categoria_codigo",
                "categoria_nome",
                "num_municipios_com_dados",
            ]
        )

    df_valido = dataframe[dataframe["valor_numerico"].notna()]

    contagem = (
        df_valido.groupby(["variavel_id", "variavel_nome", "categoria_codigo", "categoria_nome"])["localidade_id"]
        .nunique()
        .reset_index()
        .rename(columns={"localidade_id": "num_municipios_com_dados"})
        .sort_values(["variavel_id", "categoria_codigo"])
    )

    return contagem


def calcular_estatisticas(
    dataframe: pd.DataFrame,
    variavel_id: str | None = None,
    categoria_codigo: str | None = None,
) -> list[EstatisticasVariavel]:
    """Calcula estatísticas descritivas para combinações produto × variável.

    Estatísticas são calculadas apenas sobre registros com valor_numerico válido.
    Valores ausentes/especiais são excluídos do cálculo.

    Args:
        dataframe: DataFrame a ser analisado.
        variavel_id: Filtrar por variável específica (None = todas).
        categoria_codigo: Filtrar por produto específico (None = todos).

    Returns:
        Lista de EstatisticasVariavel com as estatísticas calculadas.
    """
    if dataframe.empty:
        return []

    df = dataframe.copy()
    if variavel_id is not None:
        df = df[df["variavel_id"] == variavel_id]
    if categoria_codigo is not None:
        df = df[df["categoria_codigo"] == categoria_codigo]

    resultados = []

    for (vid, vnome, vunid, ccod, cnome), grupo in df.groupby(
        ["variavel_id", "variavel_nome", "variavel_unidade", "categoria_codigo", "categoria_nome"]
    ):
        valores = grupo["valor_numerico"].dropna()
        total = len(grupo)
        validos = len(valores)
        ausentes = total - validos

        resultados.append(
            EstatisticasVariavel(
                variavel_id=str(vid),
                variavel_nome=str(vnome),
                variavel_unidade=str(vunid),
                categoria_codigo=str(ccod),
                categoria_nome=str(cnome),
                total_registros=total,
                registros_validos=validos,
                registros_ausentes=ausentes,
                minimo=float(valores.min()) if validos > 0 else None,
                maximo=float(valores.max()) if validos > 0 else None,
                media=float(valores.mean()) if validos > 0 else None,
                mediana=float(valores.median()) if validos > 0 else None,
            )
        )

    return sorted(resultados, key=lambda e: (e.variavel_id, e.categoria_codigo))


def ranking_municipios(
    dataframe: pd.DataFrame,
    variavel_id: str,
    categoria_codigo: str,
    n: int = 10,
) -> ResultadoRanking:
    """Identifica os N municípios com maiores e menores valores.

    Apenas registros com valor_numerico válido são considerados.

    Args:
        dataframe: DataFrame a ser analisado.
        variavel_id: Código da variável.
        categoria_codigo: Código do produto/categoria.
        n: Número de municípios no ranking (padrão: 10).

    Returns:
        ResultadoRanking com os rankings de maiores e menores.
    """
    df_filtrado = dataframe[
        (dataframe["variavel_id"] == variavel_id)
        & (dataframe["categoria_codigo"] == categoria_codigo)
        & (dataframe["valor_numerico"].notna())
    ].copy()

    if df_filtrado.empty:
        return ResultadoRanking(
            variavel_id=variavel_id,
            variavel_nome="",
            variavel_unidade="",
            categoria_codigo=categoria_codigo,
            categoria_nome="",
            maiores=[],
            menores=[],
        )

    # Ordena por valor descendente para maiores
    df_ordenado = df_filtrado.sort_values("valor_numerico", ascending=False)

    vnome = str(df_ordenado["variavel_nome"].iloc[0])
    vunid = str(df_ordenado["variavel_unidade"].iloc[0])
    cnome = str(df_ordenado["categoria_nome"].iloc[0])

    maiores = [
        RegistroRanking(
            localidade_id=str(row["localidade_id"]),
            localidade_nome=str(row["localidade_nome"]),
            valor_numerico=float(row["valor_numerico"]),
        )
        for _, row in df_ordenado.head(n).iterrows()
    ]

    menores = [
        RegistroRanking(
            localidade_id=str(row["localidade_id"]),
            localidade_nome=str(row["localidade_nome"]),
            valor_numerico=float(row["valor_numerico"]),
        )
        for _, row in df_ordenado.tail(n).iloc[::-1].iterrows()
    ]

    return ResultadoRanking(
        variavel_id=variavel_id,
        variavel_nome=vnome,
        variavel_unidade=vunid,
        categoria_codigo=categoria_codigo,
        categoria_nome=cnome,
        maiores=maiores,
        menores=menores,
    )


def verificar_unidades(dataframe: pd.DataFrame) -> list[ResumoUnidades]:
    """Verifica se existe mais de uma unidade para a mesma variável.

    Args:
        dataframe: DataFrame a ser analisado.

    Returns:
        Lista de ResumoUnidades com a verificação para cada variável.
    """
    if dataframe.empty:
        return []

    resultados = []

    for vid, grupo in dataframe.groupby("variavel_id"):
        vnome = str(grupo["variavel_nome"].iloc[0])
        unidades = sorted(grupo["variavel_unidade"].unique().tolist())

        resultados.append(
            ResumoUnidades(
                variavel_id=str(vid),
                variavel_nome=vnome,
                unidades_encontradas=unidades,
                consistente=len(unidades) == 1,
            )
        )

    return sorted(resultados, key=lambda r: r.variavel_id)


def verificar_duplicidades(dataframe: pd.DataFrame) -> int:
    """Verifica duplicidades usando a chave lógica do dataset.

    Chave: (variavel_id, classificacao_id, categoria_codigo,
            localidade_id, periodo)

    Args:
        dataframe: DataFrame a ser analisado.

    Returns:
        Número de registros duplicados.
    """
    if dataframe.empty:
        return 0

    chave = [
        "variavel_id",
        "classificacao_id",
        "categoria_codigo",
        "localidade_id",
        "periodo",
    ]

    colunas_presentes = [c for c in chave if c in dataframe.columns]
    total = len(dataframe)
    unicas = len(dataframe.drop_duplicates(subset=colunas_presentes))

    return total - unicas


def resumir_dataset(dataframe: pd.DataFrame) -> ResumoGeral:
    """Gera um resumo completo do dataset.

    Args:
        dataframe: DataFrame a ser resumido.

    Returns:
        ResumoGeral com todas as informações analíticas.
    """
    variaveis = listar_variaveis(dataframe)
    produtos = listar_produtos(dataframe)
    unidades = verificar_unidades(dataframe)
    estatisticas = calcular_estatisticas(dataframe)
    duplicidades = verificar_duplicidades(dataframe)

    # Contar municípios únicos
    num_municipios = 0
    if "localidade_id" in dataframe.columns:
        num_municipios = int(dataframe["localidade_id"].nunique())

    # Períodos
    periodos: list[str] = []
    if "periodo" in dataframe.columns:
        periodos = sorted(dataframe["periodo"].dropna().unique().tolist())

    # Rankings para cada combinação
    rankings = []
    for est in estatisticas:
        if est.registros_validos > 0:
            ranking = ranking_municipios(
                dataframe, est.variavel_id, est.categoria_codigo, n=10
            )
            rankings.append(ranking)

    return ResumoGeral(
        num_linhas=len(dataframe),
        num_colunas=len(dataframe.columns),
        variaveis=variaveis,
        produtos=produtos,
        num_municipios=num_municipios,
        num_periodos=periodos,
        unidades_por_variavel=unidades,
        estatisticas=estatisticas,
        rankings=rankings,
        duplicidades=duplicidades,
    )
