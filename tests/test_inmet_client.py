"""Testes unitários para client INMET."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from agrodata.pipelines.inmet.client import (
    INMETClient,
    INMETConnectionError,
    INMETResponseError,
    INMETTimeoutError,
)


class TestINMETClient:
    def test_construir_url(self):
        client = INMETClient()
        url = client._construir_url(2023)
        assert url == "https://portal.inmet.gov.br/dadoshistoricos/2023/BDMEP_2023.zip"

    def test_ano_invalido_download(self):
        client = INMETClient()
        with pytest.raises(ValueError):
            client.download_anual(1999, Path("/tmp"))

    def test_ano_invalido_acima(self):
        client = INMETClient()
        with pytest.raises(ValueError):
            client.download_anual(2031, Path("/tmp"))

    @patch("agrodata.pipelines.inmet.client.httpx.Client")
    def test_download_sucesso_200(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes.return_value = [b"chunk1", b"chunk2"]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_client.stream.return_value = mock_response

        client = INMETClient()
        client._client = mock_client

        destino = client.download_anual(2023, tmp_path)

        assert destino.exists()
        assert destino.name == "BDMEP_2023.zip"
        mock_client.stream.assert_called_once()

    @patch("agrodata.pipelines.inmet.client.httpx.Client")
    def test_download_404(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_client.stream.return_value = mock_response

        client = INMETClient()
        client._client = mock_client

        with pytest.raises(INMETResponseError) as exc_info:
            client.download_anual(2023, tmp_path)

        assert exc_info.value.status_code == 404

    @patch("agrodata.pipelines.inmet.client.httpx.Client")
    def test_download_500_retry(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.__enter__ = MagicMock(return_value=mock_response_500)
        mock_response_500.__exit__ = MagicMock(return_value=None)

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.iter_bytes.return_value = [b"data"]
        mock_response_200.__enter__ = MagicMock(return_value=mock_response_200)
        mock_response_200.__exit__ = MagicMock(return_value=None)

        mock_client.stream.side_effect = [mock_response_500, mock_response_200]

        client = INMETClient(max_retries=2, retry_delay=0.01)
        client._client = mock_client

        destino = client.download_anual(2023, tmp_path)

        assert destino.exists()
        assert mock_client.stream.call_count == 2

    @patch("agrodata.pipelines.inmet.client.httpx.Client")
    def test_download_timeout(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.stream.side_effect = httpx.TimeoutException("Timeout")

        client = INMETClient(max_retries=2, retry_delay=0.01, timeout=0.001)
        client._client = mock_client

        with pytest.raises(INMETTimeoutError):
            client.download_anual(2023, tmp_path)

    @patch("agrodata.pipelines.inmet.client.httpx.Client")
    def test_download_connection_error(self, mock_client_class, tmp_path):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.stream.side_effect = httpx.ConnectError("Connection failed")

        client = INMETClient(max_retries=2, retry_delay=0.01)
        client._client = mock_client

        with pytest.raises(INMETConnectionError):
            client.download_anual(2023, tmp_path)

    def test_context_manager(self):
        with INMETClient() as client:
            assert client._client is not None
        # client should be closed after context