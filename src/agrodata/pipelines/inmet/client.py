"""Cliente HTTP para download de dados INMET/BDMEP."""

from __future__ import annotations

import logging
import time
import types
from pathlib import Path
from typing import Self

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://portal.inmet.gov.br/dadoshistoricos"

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0
CHUNK_SIZE = 8192


class INMETClientError(Exception):
    """Exceção base para erros do cliente INMET."""


class INMETConnectionError(INMETClientError):
    """Exceção para erros de conexão."""


class INMETTimeoutError(INMETClientError):
    """Exceção para timeout na requisição."""


class INMETResponseError(INMETClientError):
    """Exceção para erros HTTP retornados pelo servidor."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class INMETClient:
    """Cliente para download de arquivos ZIP anuais do BDMEP.

    Exemplo de uso:
        client = INMETClient()
        zip_path = client.download_anual(2023, Path("data/raw/inmet/2023"))
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
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

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

    def _construir_url(self, ano: int) -> str:
        """Constrói a URL para download do ZIP anual do BDMEP."""
        return f"{BASE_URL}/{ano}/BDMEP_{ano}.zip"

    def _executar_download(self, url: str, destino: Path) -> httpx.Response:
        """Executa o download com streaming e retry para erros transitórios."""
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Download tentativa %d/%d: GET %s", attempt, self.max_retries, url)
                with self._client.stream("GET", url) as response:
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

                    destino.parent.mkdir(parents=True, exist_ok=True)
                    with destino.open("wb") as f:
                        for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                            f.write(chunk)

                    logger.info("Download concluído: %s (%.2f MB)", destino, destino.stat().st_size / 1e6)
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
                raise INMETResponseError(
                    f"Erro HTTP {exc.response.status_code}: {exc.response.text}",
                    status_code=exc.response.status_code,
                ) from exc

        if isinstance(last_exception, httpx.TimeoutException):
            raise INMETTimeoutError(f"Timeout após {self.max_retries} tentativas") from last_exception

        if isinstance(last_exception, httpx.ConnectError):
            raise INMETConnectionError(f"Erro de conexão após {self.max_retries} tentativas") from last_exception

        raise INMETClientError("Erro desconhecido durante o download")

    def download_anual(self, ano: int, destino_dir: Path) -> Path:
        """Baixa o ZIP anual do BDMEP para o diretório de destino.

        Args:
            ano: Ano do arquivo (ex: 2023).
            destino_dir: Diretório onde o ZIP será salvo.

        Returns:
            Path do arquivo ZIP baixado.

        Raises:
            INMETResponseError: Para erros HTTP não recuperáveis (ex: 404).
            INMETTimeoutError: Para timeout após esgotar tentativas.
            INMETConnectionError: Para erros de conexão após esgotar tentativas.
        """
        if not (2000 <= ano <= 2030):
            raise ValueError(f"Ano fora do intervalo suportado: {ano}")

        url = self._construir_url(ano)
        destino = destino_dir / f"BDMEP_{ano}.zip"

        logger.info("Iniciando download BDMEP %d: %s", ano, url)
        self._executar_download(url, destino)
        return destino

    def verificar_disponibilidade(self, ano: int) -> bool:
        """Verifica se o arquivo ZIP está disponível (HEAD request).

        Args:
            ano: Ano a verificar.

        Returns:
            True se disponível (200), False caso contrário.
        """
        url = self._construir_url(ano)
        try:
            response = self._client.head(url, timeout=10.0)
            return response.status_code == 200
        except httpx.RequestError:
            return False