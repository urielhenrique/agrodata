"""Orquestração do pipeline IBGE/PAM — Pesquisa Agrícola Municipal."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from agrodata.pipelines.ibge.analytics import transformar_long_para_wide
from agrodata.pipelines.ibge.client import IBGEClient
from agrodata.pipelines.ibge.load import (
    registros_para_dataframe,
    salvar_parquet,
)
from agrodata.pipelines.ibge.quality import (
    verificar_duplicidade,
    verificar_nulos,
    verificar_schema,
)
from agrodata.pipelines.ibge.transform import transformar_resposta_pam

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API de localidades do IBGE
# ---------------------------------------------------------------------------

LOCALIDADES_BASE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades"

# ---------------------------------------------------------------------------
# Classificação de produtos (tabela 782 do SIDRA)
# ---------------------------------------------------------------------------

CLASSIFICACAO_PRODUTOS_ID = "782"

# ---------------------------------------------------------------------------
# Configuração do pipeline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigPipelinePAM:
    """Configuração explícita e tipada para o pipeline IBGE/PAM.

    Valores padrão reproduzem o experimento validado:
    - 853 municípios de MG
    - 2 produtos (Soja e Milho)
    - 4 variáveis
    - Período 2023
    """

    estado_codigo: str = "31"
    estado_sigla: str = "MG"
    periodo: str = "2023"
    variaveis: list[str] = field(default_factory=lambda: ["8331", "214", "112", "215"])
    produtos: list[str] = field(default_factory=lambda: ["40124", "40122"])
    nivel_territorial: str = "N6"
    tamanho_lote: int = 200
    agregado: int = 5457
    classificacao_id: str = CLASSIFICACAO_PRODUTOS_ID

    def __post_init__(self) -> None:
        if self.tamanho_lote <= 0:
            raise ValueError(f"Tamanho do lote deve ser positivo: {self.tamanho_lote}")

    def descricao_produtos(self) -> str:
        """Gera string descritiva dos produtos para nomes de arquivo."""
        mapa = {
            "40124": "soja",
            "40122": "milho",
        }
        partes = [mapa.get(p, p) for p in self.produtos]
        return "_".join(sorted(partes))


# ---------------------------------------------------------------------------
# Métricas de execução
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricasPipeline:
    """Métricas de execução do pipeline."""

    config: ConfigPipelinePAM
    num_municipios: int
    num_lotes: int
    tamanho_lote: int
    registros_recebidos: int
    registros_transformados: int
    linhas_dataframe: int
    linhas_analytics: int
    tempo_total_seg: float
    tempo_consulta_seg: float
    tempo_transformacao_seg: float
    tempo_quality_seg: float
    tempo_analytics_seg: float
    caminho_raw: str
    caminho_parquet: str
    caminho_analytics: str


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------


def _obter_municipios(estado_codigo: str) -> list[dict[str, Any]]:
    """Obtém a lista de municípios de um estado via API de localidades do IBGE.

    Args:
        estado_codigo: Código IBGE do estado (ex: "31" para MG).

    Returns:
        Lista de dicts com 'id' e 'nome' de cada município.

    Raises:
        httpx.HTTPStatusError: Se a API retornar erro.
        httpx.ConnectError: Se não conseguir conectar.
    """
    url = f"{LOCALIDADES_BASE_URL}/estados/{estado_codigo}/municipios"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        dados = response.json()
    return [{"id": str(m["id"]), "nome": m["nome"]} for m in dados]


def _dividir_em_lotes(
    itens: list[Any], tamanho_lote: int
) -> list[list[Any]]:
    """Divide uma lista em lotes de tamanho fixo.

    Args:
        itens: Lista de itens a dividir.
        tamanho_lote: Tamanho máximo de cada lote.

    Returns:
        Lista de lotes.
    """
    if tamanho_lote <= 0:
        raise ValueError(f"Tamanho do lote deve ser positivo: {tamanho_lote}")
    return [itens[i : i + tamanho_lote] for i in range(0, len(itens), tamanho_lote)]


def _gerar_nome_base(config: ConfigPipelinePAM) -> str:
    """Gera o nome base dos arquivos a partir da configuração.

    Formato: pam_{agregado}_{periodo}_{sigla}_{produtos}
    Exemplo: pam_5457_2023_mg_soja_milho
    """
    return f"pam_{config.agregado}_{config.periodo}_{config.estado_sigla.lower()}_{config.descricao_produtos()}"


def _caminho_raw(config: ConfigPipelinePAM, raiz: Path) -> Path:
    """Retorna o caminho do arquivo RAW JSON."""
    return raiz / "data" / "raw" / "ibge" / "pam" / f"{_gerar_nome_base(config)}.json"


def _caminho_parquet(config: ConfigPipelinePAM, raiz: Path) -> Path:
    """Retorna o caminho do arquivo Parquet normalizado."""
    return raiz / "data" / "processed" / "ibge" / "pam" / f"{_gerar_nome_base(config)}.parquet"


def _caminho_analytics(config: ConfigPipelinePAM, raiz: Path) -> Path:
    """Retorna o caminho do arquivo Parquet analítico."""
    return raiz / "data" / "processed" / "ibge" / "pam" / f"{_gerar_nome_base(config)}_analytics.parquet"


def _carregar_raw_existente(caminho: Path) -> list[dict[str, Any]]:
    """Carrega um arquivo RAW JSON existente.

    Args:
        caminho: Caminho do arquivo RAW.

    Returns:
        Conteúdo do JSON como lista de dicts.
    """
    with caminho.open(encoding="utf-8") as f:
        return json.load(f)


def _salvar_raw(dados: list[dict[str, Any]], caminho: Path) -> None:
    """Salva dados brutos em formato JSON.

    Args:
        dados: Dados a salvar.
        caminho: Caminho do arquivo de saída.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def executar_pipeline(
    config: ConfigPipelinePAM | None = None,
    *,
    raiz: Path | None = None,
    permitir_sobrescrever_raw: bool = False,
    reutilizar_raw: bool = True,
) -> MetricasPipeline:
    """Executa o pipeline completo IBGE/PAM.

    Fluxo:
        1. Obter municípios do estado via API de localidades.
        2. Dividir municípios em lotes.
        3. Consultar SIDRA por lote.
        4. Consolidar respostas.
        5. Salvar RAW JSON (ou reutilizar existente).
        6. Transformar em RegistroAgricola[].
        7. Criar DataFrame.
        8. Executar Data Quality.
        9. Salvar Parquet normalizado.
        10. Transformar para wide analítico.
        11. Salvar Parquet analítico.

    Args:
        config: Configuração do pipeline. Usa padrões se None.
        raiz: Diretório raiz do projeto. Auto-detecta se None.
        permitir_sobrescrever_raw: Se True, sobrescreve RAW existente.
        reutilizar_raw: Se True e RAW existir, reutiliza sem consultar API.

    Returns:
        Métricas de execução do pipeline.

    Raises:
        FileExistsError: Se RAW já existe e nenhuma política foi definida.
        RuntimeError: Se falha de qualidade crítica for detectada.
    """
    if config is None:
        config = ConfigPipelinePAM()

    if raiz is None:
        raiz = Path(__file__).resolve().parents[3]

    logger.info("Iniciando pipeline IBGE/PAM")
    logger.info(
        "Config: estado=%s (%s), periodo=%s, variaveis=%s, produtos=%s, "
        "nivel=%s, lote=%d",
        config.estado_sigla,
        config.estado_codigo,
        config.periodo,
        config.variaveis,
        config.produtos,
        config.nivel_territorial,
        config.tamanho_lote,
    )

    tempo_inicio = time.perf_counter()

    # --- Caminhos ---
    caminho_raw = _caminho_raw(config, raiz)
    caminho_parquet = _caminho_parquet(config, raiz)
    caminho_analytics = _caminho_analytics(config, raiz)

    # --- Etapa 1-4: Consulta à API (ou reutilização de RAW) ---
    tempo_consulta_inicio = time.perf_counter()

    if caminho_raw.exists() and reutilizar_raw:
        logger.info("RAW existente encontrado: %s — reutilizando", caminho_raw)
        respostas_lotes = _carregar_raw_existente(caminho_raw)
        respostas_lotes = [respostas_lotes]  # Envolve em lista para unificação
        num_municipios = 0
        num_lotes = 1
    else:
        if caminho_raw.exists() and not permitir_sobrescrever_raw:
            raise FileExistsError(
                f"RAW já existe: {caminho_raw}. "
                "Use permitir_sobrescrever_raw=True ou reutilizar_raw=True."
            )

        # Etapa 1: Obter municípios
        logger.info("Obtendo municípios do estado %s...", config.estado_codigo)
        municipios = _obter_municipios(config.estado_codigo)
        num_municipios = len(municipios)
        logger.info("Municípios obtidos: %d", num_municipios)

        # Etapa 2: Dividir em lotes
        lotes = _dividir_em_lotes(
            [m["id"] for m in municipios], config.tamanho_lote
        )
        num_lotes = len(lotes)
        logger.info("Municípios divididos em %d lote(s) de até %d", num_lotes, config.tamanho_lote)

        # Etapa 3: Consultar SIDRA
        respostas_lotes = []
        with IBGEClient() as client:
            for i, lote in enumerate(lotes, 1):
                logger.info(
                    "Consultando lote %d/%d (%d municípios)...",
                    i,
                    num_lotes,
                    len(lote),
                )
                resposta = client.consultar_agregado(
                    agregado=config.agregado,
                    periodo=config.periodo,
                    variaveis=config.variaveis,
                    nivel_territorial=config.nivel_territorial,
                    localidades=lote,
                    classificacoes={config.classificacao_id: config.produtos},
                )
                respostas_lotes.append(resposta)
                logger.info(
                    "Lote %d/%d: %d elementos recebidos",
                    i,
                    num_lotes,
                    len(resposta),
                )

        # Etapa 5: Salvar RAW
        # Consolida todas as respostas dos lotes em uma lista plana
        respostas_consolidadas = []
        for resposta in respostas_lotes:
            respostas_consolidadas.extend(resposta)
        _salvar_raw(respostas_consolidadas, caminho_raw)
        logger.info("RAW salvo: %s", caminho_raw)

        # Re-envolve para processamento uniforme
        respostas_lotes = [respostas_consolidadas]

    tempo_consulta = time.perf_counter() - tempo_consulta_inicio

    # --- Etapa 6: Transformação ---
    tempo_transformacao_inicio = time.perf_counter()

    registros = []
    for resposta in respostas_lotes:
        registros.extend(transformar_resposta_pam(resposta))
    num_registros_recebidos = sum(len(r) for r in respostas_lotes)
    num_registros_transformados = len(registros)

    logger.info(
        "Registros: %d recebidos, %d transformados",
        num_registros_recebidos,
        num_registros_transformados,
    )

    tempo_transformacao = time.perf_counter() - tempo_transformacao_inicio

    # --- Etapa 7: DataFrame ---
    df = registros_para_dataframe(registros)
    logger.info("DataFrame: %d linhas, %d colunas", len(df), len(df.columns))

    # --- Etapa 8: Data Quality ---
    tempo_quality_inicio = time.perf_counter()

    resultado_schema = verificar_schema(df)
    if not resultado_schema.valido:
        raise RuntimeError(
            f"Falha de qualidade - schema inválido: "
            f"ausentes={resultado_schema.colunas_ausentes}, "
            f"extras={resultado_schema.colunas_extras}"
        )

    resultado_nulos = verificar_nulos(df)
    if not resultado_nulos.valido:
        raise RuntimeError(
            f"Falha de qualidade - nulos em colunas obrigatórias: "
            f"{resultado_nulos.nulos_por_coluna}"
        )

    resultado_duplicidade = verificar_duplicidade(df)
    if not resultado_duplicidade.valido:
        raise RuntimeError(
            f"Falha de qualidade - duplicidade: "
            f"{resultado_duplicidade.duplicatas} duplicatas encontradas"
        )

    logger.info("Data Quality: todas as verificações críticas passaram")
    logger.info(
        "Quality: schema=%s, nulos=%s, duplicidades=%d",
        resultado_schema.valido,
        resultado_nulos.valido,
        resultado_duplicidade.duplicatas,
    )

    tempo_quality = time.perf_counter() - tempo_quality_inicio

    # --- Etapa 9: Salvar Parquet normalizado ---
    salvar_parquet(df, caminho_parquet)
    logger.info("Parquet normalizado salvo: %s", caminho_parquet)

    # --- Etapa 10-11: Dataset analítico ---
    tempo_analytics_inicio = time.perf_counter()

    df_analytics = transformar_long_para_wide(df)
    logger.info(
        "Dataset analítico: %d linhas, %d colunas",
        len(df_analytics),
        len(df_analytics.columns),
    )

    # --- Etapa 12: Salvar Parquet analítico ---
    salvar_parquet(df_analytics, caminho_analytics)
    logger.info("Parquet analítico salvo: %s", caminho_analytics)

    tempo_analytics = time.perf_counter() - tempo_analytics_inicio
    tempo_total = time.perf_counter() - tempo_inicio

    logger.info("Pipeline concluído em %.2fs", tempo_total)

    return MetricasPipeline(
        config=config,
        num_municipios=num_municipios,
        num_lotes=num_lotes,
        tamanho_lote=config.tamanho_lote,
        registros_recebidos=num_registros_recebidos,
        registros_transformados=num_registros_transformados,
        linhas_dataframe=len(df),
        linhas_analytics=len(df_analytics),
        tempo_total_seg=round(tempo_total, 3),
        tempo_consulta_seg=round(tempo_consulta, 3),
        tempo_transformacao_seg=round(tempo_transformacao, 3),
        tempo_quality_seg=round(tempo_quality, 3),
        tempo_analytics_seg=round(tempo_analytics, 3),
        caminho_raw=str(caminho_raw.resolve()),
        caminho_parquet=str(caminho_parquet.resolve()),
        caminho_analytics=str(caminho_analytics.resolve()),
    )
