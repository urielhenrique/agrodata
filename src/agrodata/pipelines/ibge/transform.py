"""Transformação da resposta aninhada da API SIDRA em registros achatados."""

from __future__ import annotations

from typing import Any

from agrodata.pipelines.ibge.schemas import RegistroAgricola


def _extrair_categoria(
    classificacoes: list[dict[str, Any]],
) -> tuple[str, str, str, str]:
    """Extrai classificação e categoria de uma lista de classificações.

    A API retorna classificacoes como uma lista, mas cada resultado
    contém exatamente uma entrada. A categoria é um dict com um único
    par código→nome.

    Returns:
        Tupla (classificacao_id, classificacao_nome, categoria_codigo, categoria_nome).
    """
    classificacao = classificacoes[0]
    cat_dict: dict[str, str] = classificacao["categoria"]
    cat_codigo, cat_nome = next(iter(cat_dict.items()))
    return (
        classificacao["id"],
        classificacao["nome"],
        cat_codigo,
        cat_nome,
    )


def _extrair_valor_numerico(valor_bruto: str) -> float | None:
    """Converte valor bruto para float quando possível.

    Valores ausentes ("-", "..", "...") retornam None.
    """
    from agrodata.pipelines.ibge.schemas import VALORES_AUSENTES

    if valor_bruto in VALORES_AUSENTES:
        return None
    try:
        return float(valor_bruto)
    except (ValueError, TypeError):
        return None


def transformar_resposta_pam(
    resposta: list[dict[str, Any]],
) -> list[RegistroAgricola]:
    """Transforma a resposta aninhada da API SIDRA em registros achatados.

    A estrutura observada nos JSONs reais é:

        resposta = [
            {  # variável
                "id": "8331",
                "variavel": "Área plantada...",
                "unidade": "Hectares",
                "resultados": [
                    {  # resultado = classificação + séries
                        "classificacoes": [{
                            "id": "782",
                            "nome": "...",
                            "categoria": {"40124": "Soja (em grão)"}
                        }],
                        "series": [{
                            "localidade": {
                                "id": "5103403",
                                "nivel": {"id": "N6", "nome": "Município"},
                                "nome": "Cuiabá (MT)"
                            },
                            "serie": {"2023": "790"}
                        }]
                    }
                ]
            }
        ]

    Cada variável pode ter múltiplos resultados.
    Cada resultado contém uma classificação (com uma categoria)
    e múltiplas séries.
    Cada série pode conter múltiplos períodos no dict "serie".

    A relação entre classificações e séries é de coexistência
    no mesmo "resultado" — cada resultado define uma combinação
    classificação+categoria, e as séries fornecem os valores
    para diferentes localidades/períodos.
    """
    registros: list[RegistroAgricola] = []

    for variavel in resposta:
        variavel_id = variavel["id"]
        variavel_nome = variavel["variavel"]
        variavel_unidade = variavel["unidade"]

        for resultado in variavel["resultados"]:
            classificacoes = resultado["classificacoes"]
            (
                classificacao_id,
                classificacao_nome,
                categoria_codigo,
                categoria_nome,
            ) = _extrair_categoria(classificacoes)

            for serie in resultado["series"]:
                localidade = serie["localidade"]
                localidade_id = localidade["id"]
                localidade_nome = localidade["nome"]
                nivel = localidade["nivel"]
                nivel_id = nivel["id"]
                nivel_nome = nivel["nome"]

                for periodo, valor_bruto in serie["serie"].items():
                    registros.append(
                        RegistroAgricola(
                            variavel_id=variavel_id,
                            variavel_nome=variavel_nome,
                            variavel_unidade=variavel_unidade,
                            classificacao_id=classificacao_id,
                            classificacao_nome=classificacao_nome,
                            categoria_codigo=categoria_codigo,
                            categoria_nome=categoria_nome,
                            localidade_id=localidade_id,
                            localidade_nome=localidade_nome,
                            nivel_territorial_id=nivel_id,
                            nivel_territorial_nome=nivel_nome,
                            periodo=periodo,
                            valor_bruto=valor_bruto,
                        )
                    )

    return registros
