"""Validações para a Malha Municipal IBGE.

Estas validações garantem a integridade e qualidade da fonte
antes de qualquer transformação. Nenhuma correção automática
é aplicada — falhas resultam em RuntimeError.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import geopandas as gpd

logger = logging.getLogger(__name__)

NUM_MUNICIPIOS_ESPERADO_MG = 853
CRS_ESPERADO = "EPSG:4674"
TAMANHO_CODIGO_MUNICIPIO = 7


@dataclass(frozen=True)
class ResultadoValidacaoMalha:
    """Resultado das validações da malha municipal."""

    num_feicoes: int
    colunas_encontradas: list[str]
    cd_mun_nulos: int
    cd_mun_duplicados: int
    cd_mun_tamanho_invalido: int
    geometrias_nulas: int
    geometrias_invalidas: int
    crs: str | None
    valido: bool
    erros: list[str] = field(default_factory=list)


def validar_malha_municipal(
    gdf: gpd.GeoDataFrame,
    *,
    num_feicoes_esperado: int = NUM_MUNICIPIOS_ESPERADO_MG,
    crs_esperado: str = CRS_ESPERADO,
) -> ResultadoValidacaoMalha:
    """Valida a malha municipal contra regras de integridade.

    Args:
        gdf: GeoDataFrame da malha municipal.
        num_feicoes_esperado: Número esperado de feições.
        crs_esperado: CRS esperado da fonte.

    Returns:
        ResultadoValidacaoMalha com detalhes da validação.
    """
    erros: list[str] = []

    # Verificar numero de feicoes
    num_feicoes = len(gdf)
    if num_feicoes != num_feicoes_esperado:
        erros.append(
            f"Numero de feicoes incorreto: {num_feicoes} (esperado {num_feicoes_esperado})"
        )

    # Verificar CD_MUN existe
    if "CD_MUN" not in gdf.columns:
        erros.append("Coluna 'CD_MUN' nao encontrada")
        return ResultadoValidacaoMalha(
            num_feicoes=num_feicoes,
            colunas_encontradas=list(gdf.columns),
            cd_mun_nulos=0,
            cd_mun_duplicados=0,
            cd_mun_tamanho_invalido=0,
            geometrias_nulas=0,
            geometrias_invalidas=0,
            crs=str(gdf.crs) if gdf.crs else None,
            valido=False,
            erros=erros,
        )

    # Verificar CD_MUN nulos
    cd_mun_nulos = int(gdf["CD_MUN"].isna().sum())
    if cd_mun_nulos > 0:
        erros.append(f"CD_MUN possui {cd_mun_nulos} valores nulos")

    # Verificar CD_MUN unico
    cd_mun_duplicados = int(gdf["CD_MUN"].duplicated().sum())
    if cd_mun_duplicados > 0:
        erros.append(f"CD_MUN possui {cd_mun_duplicados} valores duplicados")

    # Verificar CD_MUN com tamanho diferente de 7
    cd_mun_str = gdf["CD_MUN"].astype(str)
    cd_mun_tamanho_invalido = int((cd_mun_str.str.len() != TAMANHO_CODIGO_MUNICIPIO).sum())
    if cd_mun_tamanho_invalido > 0:
        erros.append(
            f"CD_MUN possui {cd_mun_tamanho_invalido} valores com tamanho diferente de {TAMANHO_CODIGO_MUNICIPIO}"
        )

    # Verificar geometry existe
    if "geometry" not in gdf.columns:
        erros.append("Coluna 'geometry' nao encontrada")
        geometrias_nulas = 0
        geometrias_invalidas = 0
    else:
        # Verificar geometrias nulas
        geometrias_nulas = int(gdf.geometry.isna().sum())
        if geometrias_nulas > 0:
            erros.append(f"Geometry possui {geometrias_nulas} valores nulos")

        # Verificar geometrias invalidas (nao aplicar buffer(0))
        geometrias_invalidas = int((~gdf.geometry.is_valid).sum())
        if geometrias_invalidas > 0:
            municipios_invalidos = gdf.loc[~gdf.geometry.is_valid, "NM_MUN"].tolist()
            erros.append(
                f"Geometry possui {geometrias_invalidas} geometrias invalidas: {municipios_invalidos}"
            )

    # Verificar CRS definido
    crs = gdf.crs
    if crs is None:
        erros.append("CRS nao definido")
    else:
        try:
            if crs.to_epsg() != 4674:
                erros.append(f"CRS incorreto: {crs} (esperado EPSG:4674)")
        except (TypeError, ValueError):
            erros.append(f"CRS nao pode ser convertido para EPSG: {crs}")

    valido = len(erros) == 0

    return ResultadoValidacaoMalha(
        num_feicoes=num_feicoes,
        colunas_encontradas=list(gdf.columns),
        cd_mun_nulos=cd_mun_nulos,
        cd_mun_duplicados=cd_mun_duplicados,
        cd_mun_tamanho_invalido=cd_mun_tamanho_invalido,
        geometrias_nulas=geometrias_nulas,
        geometrias_invalidas=geometrias_invalidas,
        crs=str(crs) if crs else None,
        valido=valido,
        erros=erros,
    )


def asserir_malha_valida(
    gdf: gpd.GeoDataFrame,
    *,
    num_feicoes_esperado: int = NUM_MUNICIPIOS_ESPERADO_MG,
    crs_esperado: str = CRS_ESPERADO,
) -> None:
    """Valida a malha e levanta exceção em caso de falha.

    Args:
        gdf: GeoDataFrame da malha municipal.

    Raises:
        RuntimeError: Se qualquer validacao falhar.
    """
    resultado = validar_malha_municipal(
        gdf, num_feicoes_esperado=num_feicoes_esperado, crs_esperado=crs_esperado
    )

    if not resultado.valido:
        logger.error("Validacao da malha falhou: %s", resultado.erros)
        raise RuntimeError(
            "Validacao da malha municipal falhou:\n" + "\n".join(resultado.erros)
        )

    logger.info(
        "Malha validada: %d feicoes, CRS=%s, geometry valida",
        resultado.num_feicoes,
        resultado.crs,
    )
