"""Cliente HTTP para a API SIDRA do IBGE."""

from __future__ import annotations

import logging
import time
import types
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Erros HTTP que justificam nova tentativa
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0


class IBGEClientError(Exception):
    """Exceção base para erros do cliente IBGE."""


class IBGEConnectionError(IBGEClientError):
    """Exceção para erros de conexão com a API."""


class IBGETimeoutError(IBGEClientError):
    """Exceção para timeout na requisição."""


class IBGEResponseError(IBGEClientError):
    """Exceção para erros HTTP retornados pela API."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class IBGEClient:
    """Cliente para consulta à API SIDRA do IBGE (tabela de agregados).

    Exemplo de uso:
        client = IBGEClient()
        dados = client.consultar_agregado(
            agregado=5457,
            periodo="2023",
            variaveis=["8331", "214"],
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes={"782": ["40124"]},
        )
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Fecha a conexão HTTP subjacente."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        self.close()

    def _construir_url(
        self,
        agregado: int,
        periodo: str,
        variaveis: list[str],
    ) -> str:
        """Constrói a URL base para consulta ao agregado.

        Args:
            agregado: Identificador da tabela SIDRA (ex: 5457).
            periodo: Período da consulta (ex: "2023", "all").
            variaveis: Lista de códigos de variáveis (ex: ["8331", "214"]).

        Returns:
            URL completa para a requisição.
        """
        variaveis_str = "|".join(variaveis)
        return f"{BASE_URL}/{agregado}/periodos/{periodo}/variaveis/{variaveis_str}"

    @staticmethod
    def _formatar_parametros(
        nivel_territorial: str,
        localidades: list[str],
        classificacoes: dict[str, list[str]] | None,
    ) -> dict[str, str]:
        """Formata os parâmetros de query da requisição.

        Args:
            nivel_territorial: Nível territorial do IBGE (ex: "N6" para município).
            localidades: Lista de códigos de localidades (ex: ["3550308"]).
            classificacoes: Dicionário de classificações (ex: {"782": ["40124"]}).
                Chave = código da classificação, valor = lista de códigos de categorias.

        Returns:
            Dicionário de parâmetros de query formatados.
        """
        codigos = ",".join(localidades)
        params: dict[str, str] = {"localidades": f"{nivel_territorial}[{codigos}]"}

        if classificacoes:
            partes = []
            for cls_id, categorias in classificacoes.items():
                cats = ",".join(categorias)
                partes.append(f"{cls_id}[{cats}]")
            params["classificacao"] = "|".join(partes)

        return params

    def _executar_requisicao(
        self,
        url: str,
        params: dict[str, str],
    ) -> httpx.Response:
        """Executa a requisição HTTP com retry para erros transitórios.

        Args:
            url: URL da requisição.
            params: Parâmetros de query.

        Returns:
            Objeto Response do httpx.

        Raises:
            IBGEResponseError: Para erros HTTP não recuperáveis.
            IBGETimeoutError: Para timeout após esgotar tentativas.
            IBGEConnectionError: Para erros de conexão após esgotar tentativas.
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "Requisição %d/%d: GET %s params=%s",
                    attempt,
                    self.max_retries,
                    url,
                    params,
                )
                response = self._client.get(url, params=params)

                if response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "Status %d recebido (tentativa %d/%d). Retry em %.1fs...",
                        response.status_code,
                        attempt,
                        self.max_retries,
                        self.retry_delay,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                        continue

                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    "Timeout na tentativa %d/%d. Retry em %.1fs...",
                    attempt,
                    self.max_retries,
                    self.retry_delay,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

            except httpx.ConnectError as exc:
                last_exception = exc
                logger.warning(
                    "Erro de conexão na tentativa %d/%d. Retry em %.1fs...",
                    attempt,
                    self.max_retries,
                    self.retry_delay,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

            except httpx.HTTPStatusError as exc:
                raise IBGEResponseError(
                    f"Erro HTTP {exc.response.status_code}: {exc.response.text}",
                    status_code=exc.response.status_code,
                ) from exc

        if isinstance(last_exception, httpx.TimeoutException):
            raise IBGETimeoutError(
                f"Timeout após {self.max_retries} tentativas"
            ) from last_exception

        if isinstance(last_exception, httpx.ConnectError):
            raise IBGEConnectionError(
                f"Erro de conexão após {self.max_retries} tentativas"
            ) from last_exception

        raise IBGEClientError("Erro desconhecido durante a requisição")

    def consultar_agregado(
        self,
        agregado: int,
        periodo: str,
        variaveis: list[str],
        nivel_territorial: str,
        localidades: list[str],
        classificacoes: dict[str, list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Consulta um agregado do IBGE na API SIDRA.

        Args:
            agregado: Identificador da tabela SIDRA (ex: 5457).
            periodo: Período da consulta (ex: "2023", "all").
            variaveis: Lista de códigos de variáveis (ex: ["8331", "214"]).
            nivel_territorial: Nível territorial do IBGE (ex: "N6" para município).
            localidades: Lista de códigos de localidades (ex: ["3550308"]).
            classificacoes: Dicionário de classificações
                (ex: {"782": ["40124"]}).

        Returns:
            Lista de dicionários com os dados retornados pela API.

        Raises:
            IBGEResponseError: Para erros HTTP não recuperáveis.
            IBGETimeoutError: Para timeout após esgotar tentativas.
            IBGEConnectionError: Para erros de conexão após esgotar tentativas.
        """
        url = self._construir_url(agregado, periodo, variaveis)
        params = self._formatar_parametros(nivel_territorial, localidades, classificacoes)

        response = self._executar_requisicao(url, params)
        return response.json()
