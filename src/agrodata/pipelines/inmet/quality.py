"""Verificações de qualidade para dados INMET/BDMEP."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from agrodata.pipelines.inmet.schemas import ObservacaoHoraria


@dataclass(frozen=True)
class QualityReport:
    """Relatório consolidado de qualidade."""

    total_registros: int
    contagem_por_flag: dict[str, int]
    contagem_por_regra: dict[str, int]
    duplicidades_pk: int
    gaps_temporais_maiores_24h: int
    estacoes_sem_metadata: int
    erros: int
    warnings: int
    valido: bool

    def to_dict(self) -> dict:
        return {
            "total_registros": self.total_registros,
            "contagem_por_flag": self.contagem_por_flag,
            "contagem_por_regra": self.contagem_por_regra,
            "duplicidades_pk": self.duplicidades_pk,
            "gaps_temporais_maiores_24h": self.gaps_temporais_maiores_24h,
            "estacoes_sem_metadata": self.estacoes_sem_metadata,
            "erros": self.erros,
            "warnings": self.warnings,
            "valido": self.valido,
        }


CHAVE_LOGICA = ["station_id", "datetime", "variable"]


def _contar_por_flag(observacoes: list[ObservacaoHoraria]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for obs in observacoes:
        contagem[obs.quality_flag] = contagem.get(obs.quality_flag, 0) + 1
    return contagem


def _verificar_missing(observacoes: list[ObservacaoHoraria]) -> int:
    return sum(1 for obs in observacoes if obs.value is None)


def _verificar_precipitacao_negativa(observacoes: list[ObservacaoHoraria]) -> int:
    return sum(
        1
        for obs in observacoes
        if obs.variable == "precipitacao" and obs.value is not None and obs.value < 0
    )


def _verificar_temp_max_menor_min(observacoes: list[ObservacaoHoraria]) -> int:
    df = pd.DataFrame([o.model_dump() for o in observacoes])
    if df.empty:
        return 0

    pivot = df.pivot_table(
        index=["station_id", "datetime"],
        columns="variable",
        values="value",
        aggfunc="first",
    ).reset_index()

    if "temp_max" not in pivot.columns or "temp_min" not in pivot.columns:
        return 0

    return int(((pivot["temp_max"] < pivot["temp_min"]) & pivot["temp_max"].notna() & pivot["temp_min"].notna()).sum())


def _verificar_temperatura_fora_faixa(observacoes: list[ObservacaoHoraria]) -> int:
    return sum(
        1
        for obs in observacoes
        if obs.variable in ("temp_max", "temp_min")
        and obs.value is not None
        and (obs.value < -50 or obs.value > 60)
    )


def _verificar_precipitacao_extrema(observacoes: list[ObservacaoHoraria]) -> int:
    return sum(
        1
        for obs in observacoes
        if obs.variable == "precipitacao" and obs.value is not None and obs.value > 500
    )


def _verificar_duplicidade_pk(observacoes: list[ObservacaoHoraria]) -> int:
    if not observacoes:
        return 0
    df = pd.DataFrame([o.model_dump() for o in observacoes])
    colunas_presentes = [c for c in CHAVE_LOGICA if c in df.columns]
    if not colunas_presentes:
        return 0
    total = len(df)
    unicas = len(df.drop_duplicates(subset=colunas_presentes))
    return total - unicas


def _verificar_gaps_temporais(observacoes: list[ObservacaoHoraria]) -> int:
    if not observacoes:
        return 0
    df = pd.DataFrame([o.model_dump() for o in observacoes])
    gaps = 0
    for station_id, group in df.groupby("station_id"):
        group = group.sort_values("datetime")
        diffs = group["datetime"].diff().dt.total_seconds()
        gaps += int((diffs > 86400).sum())
    return gaps


def _verificar_estacao_sem_metadata(
    observacoes: list[ObservacaoHoraria], estacoes_conhecidas: set[str]
) -> int:
    estacoes_dados = {obs.station_id for obs in observacoes}
    return len(estacoes_dados - estacoes_conhecidas)


def verificar_qualidade(
    observacoes: list[ObservacaoHoraria],
    estacoes_conhecidas: set[str] | None = None,
) -> QualityReport:
    """Executa todas as 8 regras de qualidade.

    Args:
        observacoes: Lista de observações normalizadas.
        estacoes_conhecidas: Set de station_ids com metadata válida (do station_catalog).

    Returns:
        QualityReport com contagens e status.
    """
    if estacoes_conhecidas is None:
        estacoes_conhecidas = set()

    contagem_por_regra = {
        "missing": _verificar_missing(observacoes),
        "precipitacao_negativa": _verificar_precipitacao_negativa(observacoes),
        "temp_max_menor_min": _verificar_temp_max_menor_min(observacoes),
        "temperatura_fora_faixa": _verificar_temperatura_fora_faixa(observacoes),
        "precipitacao_extrema": _verificar_precipitacao_extrema(observacoes),
        "duplicidade_pk": _verificar_duplicidade_pk(observacoes),
        "gaps_temporais_24h": _verificar_gaps_temporais(observacoes),
        "estacao_sem_metadata": _verificar_estacao_sem_metadata(observacoes, estacoes_conhecidas),
    }

    contagem_por_flag = _contar_por_flag(observacoes)

    erros = contagem_por_regra["duplicidade_pk"] + contagem_por_regra["temperatura_fora_faixa"]
    warnings = (
        contagem_por_regra["precipitacao_negativa"]
        + contagem_por_regra["temp_max_menor_min"]
        + contagem_por_regra["precipitacao_extrema"]
        + contagem_por_regra["gaps_temporais_24h"]
        + contagem_por_regra["estacao_sem_metadata"]
    )

    return QualityReport(
        total_registros=len(observacoes),
        contagem_por_flag=contagem_por_flag,
        contagem_por_regra=contagem_por_regra,
        duplicidades_pk=contagem_por_regra["duplicidade_pk"],
        gaps_temporais_maiores_24h=contagem_por_regra["gaps_temporais_24h"],
        estacoes_sem_metadata=contagem_por_regra["estacao_sem_metadata"],
        erros=erros,
        warnings=warnings,
        valido=erros == 0,
    )