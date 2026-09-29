"""Testes para o cliente IBGE."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from agrodata.pipelines.ibge.client import (
    IBGEClient,
    IBGEConnectionError,
    IBGEResponseError,
    IBGETimeoutError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> IBGEClient:
    """Cria um cliente IBGE para testes."""
    return IBGEClient(timeout=5.0, max_retries=3, retry_delay=0.0)


@pytest.fixture()
def resposta_sucesso() -> MagicMock:
    """Cria uma resposta HTTP de sucesso simulada."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = [
        {
            "id": "8331",
            "variavel": "Área plantada ou destinada à colheita",
            "unidade": "Hectares",
            "resultados": [
                {
                    "classificacoes": [
                        {
                            "id": "782",
                            "nome": "Produto das lavouras temporárias e permanentes",
                            "categoria": {"40124": "Soja (em grão)"},
                        }
                    ],
                    "series": [
                        {
                            "localidade": {
                                "id": "5103403",
                                "nivel": {"id": "N6", "nome": "Município"},
                                "nome": "Cuiabá (MT)",
                            },
                            "serie": {"2023": "790"},
                        }
                    ],
                }
            ],
        }
    ]
    return response


# ---------------------------------------------------------------------------
# Testes de construção de URL
# ---------------------------------------------------------------------------


class TestConstrucaoURL:
    """Testes para construção da URL da requisição."""

    def test_url_completa_variavel_unica(self, client: IBGEClient) -> None:
        url = client._construir_url(
            agregado=5457, periodo="2023", variaveis=["8331"]
        )
        esperado = (
            "https://servicodados.ibge.gov.br/api/v3/agregados"
            "/5457/periodos/2023/variaveis/8331"
        )
        assert url == esperado

    def test_url_completa_variaveis_multiplas(self, client: IBGEClient) -> None:
        url = client._construir_url(
            agregado=5457, periodo="2023", variaveis=["8331", "214", "215"]
        )
        esperado = (
            "https://servicodados.ibge.gov.br/api/v3/agregados"
            "/5457/periodos/2023/variaveis/8331|214|215"
        )
        assert url == esperado

    def test_url_com_periodo_all(self, client: IBGEClient) -> None:
        url = client._construir_url(
            agregado=5457, periodo="all", variaveis=["8331"]
        )
        esperado = (
            "https://servicodados.ibge.gov.br/api/v3/agregados"
            "/5457/periodos/all/variaveis/8331"
        )
        assert url == esperado

    def test_url_outro_agregado(self, client: IBGEClient) -> None:
        url = client._construir_url(
            agregado=1618, periodo="2024", variaveis=["109", "216"]
        )
        esperado = (
            "https://servicodados.ibge.gov.br/api/v3/agregados"
            "/1618/periodos/2024/variaveis/109|216"
        )
        assert url == esperado


# ---------------------------------------------------------------------------
# Testes de parâmetros de query — localidades com nível territorial
# ---------------------------------------------------------------------------


class TestParametrosLocalidades:
    """Testes para formatação de localidades com nível territorial."""

    def test_localidade_unica_n6(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes=None,
        )
        assert params["localidades"] == "N6[3550308]"

    def test_localidades_multiplas_n6(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308", "5103403"],
            classificacoes=None,
        )
        assert params["localidades"] == "N6[3550308,5103403]"

    def test_nivel_n1_brasil(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N1",
            localidades=["1"],
            classificacoes=None,
        )
        assert params["localidades"] == "N1[1]"

    def test_nivel_n2_regiao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N2",
            localidades=["1", "2", "3"],
            classificacoes=None,
        )
        assert params["localidades"] == "N2[1,2,3]"

    def test_nivel_n3_uf(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N3",
            localidades=["35", "51"],
            classificacoes=None,
        )
        assert params["localidades"] == "N3[35,51]"

    def test_nivel_n8_mesorregiao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N8",
            localidades=["35001", "35002"],
            classificacoes=None,
        )
        assert params["localidades"] == "N8[35001,35002]"

    def test_nivel_n9_microrregiao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N9",
            localidades=["3500100"],
            classificacoes=None,
        )
        assert params["localidades"] == "N9[3500100]"


# ---------------------------------------------------------------------------
# Testes de parâmetros de query — classificações
# ---------------------------------------------------------------------------


class TestParametrosClassificacoes:
    """Testes para formatação de classificações."""

    def test_classificacao_unica(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes={"782": ["40124"]},
        )
        assert params["localidades"] == "N6[3550308]"
        assert params["classificacao"] == "782[40124]"

    def test_classificacao_multipla(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes={"782": ["40124", "40122"]},
        )
        assert params["classificacao"] == "782[40124,40122]"

    def test_multiplas_classificacoes(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes={"782": ["40124"], "783": ["1"]},
        )
        assert "782[40124]" in params["classificacao"]
        assert "783[1]" in params["classificacao"]

    def test_sem_classificacao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes=None,
        )
        assert "classificacao" not in params

    def test_classificacao_vazia(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["3550308"],
            classificacoes={},
        )
        assert "classificacao" not in params


# ---------------------------------------------------------------------------
# Testes de parâmetros combinados
# ---------------------------------------------------------------------------


class TestParametrosCombinados:
    """Testes para localidades e classificações combinadas."""

    def test_n6_com_classificacao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N6",
            localidades=["5103403", "3550308"],
            classificacoes={"782": ["40124", "40122"]},
        )
        assert params["localidades"] == "N6[5103403,3550308]"
        assert params["classificacao"] == "782[40124,40122]"

    def test_n3_uf_com_classificacao(self, client: IBGEClient) -> None:
        params = client._formatar_parametros(
            nivel_territorial="N3",
            localidades=["51", "35"],
            classificacoes={"782": ["40124"]},
        )
        assert params["localidades"] == "N3[51,35]"
        assert params["classificacao"] == "782[40124]"


# ---------------------------------------------------------------------------
# Testes de requisição HTTP
# ---------------------------------------------------------------------------


class TestRequisicaoHTTP:
    """Testes para execução de requisições HTTP."""

    @patch("agrodata.pipelines.ibge.client.IBGEClient._executar_requisicao")
    def test_sucesso_http(
        self,
        mock_executar: MagicMock,
        client: IBGEClient,
        resposta_sucesso: MagicMock,
    ) -> None:
        mock_executar.return_value = resposta_sucesso

        dados = client.consultar_agregado(
            agregado=5457,
            periodo="2023",
            variaveis=["8331"],
            nivel_territorial="N6",
            localidades=["5103403"],
            classificacoes={"782": ["40124"]},
        )

        assert len(dados) == 1
        assert dados[0]["id"] == "8331"
        assert dados[0]["variavel"] == "Área plantada ou destinada à colheita"

    @patch("httpx.Client.get")
    def test_erro_http_404(
        self, mock_get: MagicMock, client: IBGEClient
    ) -> None:
        mock_get.return_value = MagicMock(
            status_code=404,
            raise_for_status=MagicMock(
                side_effect=httpx.HTTPStatusError(
                    message="Not Found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            ),
        )

        with pytest.raises(IBGEResponseError) as exc_info:
            client.consultar_agregado(
                agregado=99999,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )

        assert exc_info.value.status_code == 404

    @patch("httpx.Client.get")
    def test_erro_http_500(
        self, mock_get: MagicMock, client: IBGEClient
    ) -> None:
        response_500 = MagicMock(status_code=500, text="Internal Server Error")
        response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="500",
            request=MagicMock(),
            response=response_500,
        )
        mock_get.return_value = response_500

        with pytest.raises(IBGEResponseError):
            client.consultar_agregado(
                agregado=5457,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )


# ---------------------------------------------------------------------------
# Testes de timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """Testes para tratamento de timeout."""

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_timeout_retry_e_excecao(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
        client: IBGEClient,
    ) -> None:
        mock_get.side_effect = httpx.TimeoutException("timeout")

        with pytest.raises(IBGETimeoutError) as exc_info:
            client.consultar_agregado(
                agregado=5457,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )

        assert "Timeout" in str(exc_info.value)
        assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# Testes de erro de conexão
# ---------------------------------------------------------------------------


class TestErroConexao:
    """Testes para tratamento de erros de conexão."""

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_conexao_retry_e_excecao(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
        client: IBGEClient,
    ) -> None:
        mock_get.side_effect = httpx.ConnectError("connection refused")

        with pytest.raises(IBGEConnectionError) as exc_info:
            client.consultar_agregado(
                agregado=5457,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )

        assert "conexão" in str(exc_info.value)
        assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# Testes de retry
# ---------------------------------------------------------------------------


class TestRetry:
    """Testes para mecanismo de retry."""

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_retry_erro_transitorio_sucesso(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
        client: IBGEClient,
        resposta_sucesso: MagicMock,
    ) -> None:
        response_503 = MagicMock(status_code=503, text="Service Unavailable")
        response_503.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="503",
            request=MagicMock(),
            response=response_503,
        )

        mock_get.side_effect = [response_503, resposta_sucesso]

        dados = client.consultar_agregado(
            agregado=5457,
            periodo="2023",
            variaveis=["8331"],
            nivel_territorial="N6",
            localidades=["5103403"],
        )

        assert len(dados) == 1
        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_retry_erro_429(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
        client: IBGEClient,
        resposta_sucesso: MagicMock,
    ) -> None:
        response_429 = MagicMock(status_code=429, text="Too Many Requests")
        response_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="429",
            request=MagicMock(),
            response=response_429,
        )

        mock_get.side_effect = [response_429, resposta_sucesso]

        dados = client.consultar_agregado(
            agregado=5457,
            periodo="2023",
            variaveis=["8331"],
            nivel_territorial="N6",
            localidades=["5103403"],
        )

        assert len(dados) == 1
        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_fala_apos_exceder_tentativas(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        mock_get.side_effect = httpx.TimeoutException("timeout")

        client_max_2 = IBGEClient(max_retries=2, retry_delay=0.0)

        with pytest.raises(IBGETimeoutError):
            client_max_2.consultar_agregado(
                agregado=5457,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )

        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    @patch("time.sleep")
    def test_nao_retry_erro_nao_transitorio(
        self,
        mock_sleep: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        response_400 = MagicMock(status_code=400, text="Bad Request")
        response_400.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="400",
            request=MagicMock(),
            response=response_400,
        )

        mock_get.return_value = response_400

        client_temp = IBGEClient(max_retries=3, retry_delay=0.0)

        with pytest.raises(IBGEResponseError):
            client_temp.consultar_agregado(
                agregado=5457,
                periodo="2023",
                variaveis=["8331"],
                nivel_territorial="N6",
                localidades=["3550308"],
            )

        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# Testes de contexto
# ---------------------------------------------------------------------------


class TestContexto:
    """Testes para uso do cliente como context manager."""

    def test_context_manager(self) -> None:
        with IBGEClient() as client:
            assert client._client is not None

    def test_close(self) -> None:
        client = IBGEClient()
        client.close()
        assert client._client.is_closed
