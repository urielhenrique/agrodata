"""Parser para arquivos CSV do INMET/BDMEP."""

from __future__ import annotations

import hashlib
import zipfile
from collections.abc import Generator
from pathlib import Path

import pandas as pd

COLUNAS_ESPERADAS = [
    "Data",
    "Hora UTC",
    "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)",
    "PRESSÃO ATMOSFÉRICA AO NÍVEL DA ESTAÇÃO, HORÁRIA (mB)",
    "PRESSÃO ATMOSFÉRICA MAX. NA HORA ANT. (AUT) (mB)",
    "PRESSÃO ATMOSFÉRICA MIN. NA HORA ANT. (AUT) (mB)",
    "RADIAÇÃO GLOBAL (KJ/m²)",
    "TEMPERATURA DO AR - BULBO SECO, HORÁRIA (°C)",
    "TEMPERATURA DO PONTO DE ORVALHO (°C)",
    "TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)",
    "TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)",
    "TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT) (°C)",
    "TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT) (°C)",
    "UMIDADE REL. MAX. NA HORA ANT. (AUT) (%)",
    "UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)",
    "UMIDADE RELATIVA DO AR, HORÁRIA (%)",
    "VENTO, DIREÇÃO HORÁRIA (graus)",
    "VENTO, RAJADA MÁXIMA (m/s)",
    "VENTO, VELOCIDADE HORÁRIA (m/s)",
]

MAPA_VARIAVEIS = {
    "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": "precipitacao",
    "TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)": "temp_max",
    "TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)": "temp_min",
}

COLUNAS_METADADOS = {
    "Região": "regiao",
    "UF": "uf",
    "Estação": "station_name",
    "Código (WMO)": "wmo_id",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Altitude": "altitude",
}


def _calcular_hash_linha(linha: str) -> str:
    """Calcula SHA256 da linha original do CSV."""
    return hashlib.sha256(linha.encode("latin-1")).hexdigest()


def _extrair_metadados_estacao(caminho_csv: Path) -> dict:
    """Extrai metadados da estação nas primeiras 8 linhas do CSV."""
    metadados = {}
    with caminho_csv.open("r", encoding="latin-1") as f:
        for i, linha in enumerate(f):
            if i >= 8:
                break
            if ";" in linha:
                chave, valor = linha.strip().split(";", 1)
                chave = chave.strip()
                valor = valor.strip()
                if chave in COLUNAS_METADADOS:
                    metadados[COLUNAS_METADADOS[chave]] = valor
    return metadados


def _parsear_coordenada(valor: str) -> float | None:
    """Converte coordenada INMET (ex: -19,92) para float."""
    if not valor or valor.strip() == "":
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def _parsear_altitude(valor: str) -> float | None:
    """Converte altitude (ex: 852,0) para float."""
    if not valor or valor.strip() == "":
        return None
    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


def listar_csvs_no_zip(zip_path: Path) -> list[str]:
    """Lista arquivos CSV dentro do ZIP."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        return [name for name in zf.namelist() if name.upper().endswith(".CSV")]


def extrair_zip(zip_path: Path, destino_dir: Path) -> list[Path]:
    """Extrai todos os CSVs do ZIP para o diretório de destino."""
    destino_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        csvs = [name for name in zf.namelist() if name.upper().endswith(".CSV")]
        zf.extractall(destino_dir, members=csvs)
        return [destino_dir / name for name in csvs]


def ler_csv_bruto(caminho_csv: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Lê CSV INMET preservando linhas brutas para hash.

    Returns:
        Tupla (DataFrame parseado, lista de hashes das linhas, lista de linhas brutas).
    """
    linhas_brutas = []
    hashes = []
    header = None

    with caminho_csv.open("r", encoding="latin-1") as f:
        for i in range(7):
            next(f)
        header_line = next(f).rstrip("\n\r")
        header = header_line.split(";")
        for linha in f:
            linha = linha.rstrip("\n\r")
            if linha:
                linhas_brutas.append(linha)
                hashes.append(_calcular_hash_linha(linha))

    if not linhas_brutas:
        return pd.DataFrame(columns=header or COLUNAS_ESPERADAS), [], []

    from io import StringIO
    conteudo = "\n".join(linhas_brutas)
    df = pd.read_csv(
        StringIO(conteudo),
        sep=";",
        decimal=",",
        encoding="latin-1",
        header=None,
        names=header,
        dtype=str,
        na_filter=False,
    )

    return df, hashes, linhas_brutas


def filtrar_variaveis_relevantes(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas colunas das 3 variáveis de interesse + data/hora."""
    colunas_manter = ["Data", "Hora UTC"] + list(MAPA_VARIAVEIS.keys())
    colunas_existentes = [c for c in colunas_manter if c in df.columns]
    return df[colunas_existentes].copy()


def parser_csv_para_registros(
    caminho_csv: Path,
    extracted_at: str,
    ingestion_run_id: str,
) -> Generator[dict]:
    """Parser principal: CSV → dicionários prontos para validação Pydantic.

    Yields:
        Dicionários com campos de ObservacaoHoraria + metadados da estação.
    """
    df, hashes, _ = ler_csv_bruto(caminho_csv)

    if df.empty:
        return

    metadados = _extrair_metadados_estacao(caminho_csv)
    station_id = caminho_csv.stem

    df = filtrar_variaveis_relevantes(df)

    for idx, row in df.iterrows():
        data_str = row["Data"]
        hora_str = row["Hora UTC"]

        try:
            dt = pd.to_datetime(f"{data_str} {hora_str}", format="%Y-%m-%d %H%M", utc=True)
        except (ValueError, TypeError):
            continue

        for coluna_original, variable in MAPA_VARIAVEIS.items():
            if coluna_original not in row:
                continue

            valor_bruto = row[coluna_original]
            raw_row_hash = hashes[idx] if idx < len(hashes) else ""

            if valor_bruto in ("", "-9999", "NaN", "nan", None):
                value = None
                quality_flag = "missing"
            else:
                try:
                    value = float(valor_bruto.replace(",", "."))
                    quality_flag = "valid"
                except (ValueError, AttributeError):
                    value = None
                    quality_flag = "missing"

            # Skip if value is missing and this variable column wasn't in the original CSV
            # (empty string means column existed but had no data)
            if value is None and quality_flag == "missing" and valor_bruto == "":
                continue

            yield {
                "station_id": station_id,
                "datetime": dt.to_pydatetime(),
                "variable": variable,
                "value": value,
                "source": "INMET_BDMEP",
                "extracted_at": extracted_at,
                "raw_row_hash": raw_row_hash,
                "ingestion_run_id": ingestion_run_id,
                "quality_flag": quality_flag,
                "_station_meta": metadados,
            }


def obter_metadados_estacao(caminho_csv: Path) -> dict:
    """Retorna metadados da estação extraídos do cabeçalho do CSV."""
    metadados = _extrair_metadados_estacao(caminho_csv)
    metadados["station_id"] = caminho_csv.stem
    return metadados