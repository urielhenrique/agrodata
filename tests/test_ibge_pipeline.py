"""Testes para o pipeline IBGE/PAM."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from agrodata.pipelines.ibge.pipeline import (
    ConfigPipelinePAM,
    MetricasPipeline,
    _caminho_analytics,
    _caminho_parquet,
    _caminho_raw,
    _dividir_em_lotes,
    _gerar_nome_base,
    _obter_municipios,
    executar_pipeline,
)
from agrodata.pipelines.ibge.schemas import RegistroAgricola

# ---------------------------------------------------------------------------
# Fixtures de dados
# ---------------------------------------------------------------------------

RESPOSTA_SIDRA = [
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
                            "id": "3100104",
                            "nivel": {"id": "N6", "nome": "Município"},
                            "nome": "Abadia dos Dourados (MG)",
                        },
                        "serie": {"2023": "4000"},
                    }
                ],
            }
        ],
    }
]

MUNICIPIOS_FAKE = [
    {"id": "3100104", "nome": "Abadia dos Dourados (MG)"},
    {"id": "3100203", "nome": "Abaeté (MG)"},
    {"id": "3100302", "nome": "Abre Campo (MG)"},
]

FIXTURES_PAM_DIR = Path(__file__).parent / "fixtures" / "ibge" / "pam"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_padrao() -> ConfigPipelinePAM:
    """Configuração padrão para testes."""
    return ConfigPipelinePAM()


@pytest.fixture()
def config_pequena() -> ConfigPipelinePAM:
    """Configuração com lote pequeno para testar divisão."""
    return ConfigPipelinePAM(tamanho_lote=2)


@pytest.fixture()
def registros_fake() -> list[RegistroAgricola]:
    """Lista de registros agrícolas para testes."""
    return [
        RegistroAgricola(
            variavel_id="8331",
            variavel_nome="Área plantada ou destinada à colheita",
            variavel_unidade="Hectares",
            classificacao_id="782",
            classificacao_nome="Produto das lavouras temporárias e permanentes",
            categoria_codigo="40124",
            categoria_nome="Soja (em grão)",
            localidade_id="3100104",
            localidade_nome="Abadia dos Dourados (MG)",
            nivel_territorial_id="N6",
            nivel_territorial_nome="Município",
            periodo="2023",
            valor_bruto="4000",
        ),
        RegistroAgricola(
            variavel_id="214",
            variavel_nome="Quantidade produzida",
            variavel_unidade="Toneladas",
            classificacao_id="782",
            classificacao_nome="Produto das lavouras temporárias e permanentes",
            categoria_codigo="40124",
            categoria_nome="Soja (em grão)",
            localidade_id="3100104",
            localidade_nome="Abadia dos Dourados (MG)",
            nivel_territorial_id="N6",
            nivel_territorial_nome="Município",
            periodo="2023",
            valor_bruto="880",
        ),
    ]


@pytest.fixture()
def dataframe_fake(registros_fake: list[RegistroAgricola]) -> pd.DataFrame:
    """DataFrame fake para testes de qualidade."""
    from agrodata.pipelines.ibge.load import registros_para_dataframe

    return registros_para_dataframe(registros_fake)


# ---------------------------------------------------------------------------
# Testes: ConfigPipelinePAM
# ---------------------------------------------------------------------------


class TestConfigPipelinePAM:
    """Testes para a configuração do pipeline."""

    def test_config_padrao(self, config_padrao: ConfigPipelinePAM) -> None:
        assert config_padrao.estado_codigo == "31"
        assert config_padrao.estado_sigla == "MG"
        assert config_padrao.periodo == "2023"
        assert config_padrao.variaveis == ["8331", "214", "112", "215"]
        assert config_padrao.produtos == ["40124", "40122"]
        assert config_padrao.nivel_territorial == "N6"
        assert config_padrao.tamanho_lote == 200
        assert config_padrao.agregado == 5457
        assert config_padrao.classificacao_id == "782"

    def test_config_frozen(self) -> None:
        config = ConfigPipelinePAM()
        with pytest.raises(AttributeError):
            config.estado_codigo = "35"  # type: ignore[misc]

    def test_config_customizada(self) -> None:
        config = ConfigPipelinePAM(
            estado_codigo="35",
            estado_sigla="SP",
            periodo="2022",
            variaveis=["8331"],
            produtos=["40124"],
            tamanho_lote=100,
        )
        assert config.estado_codigo == "35"
        assert config.estado_sigla == "SP"
        assert config.periodo == "2022"
        assert config.variaveis == ["8331"]
        assert config.produtos == ["40124"]
        assert config.tamanho_lote == 100

    def test_descricao_produtos(self, config_padrao: ConfigPipelinePAM) -> None:
        assert config_padrao.descricao_produtos() == "milho_soja"

    def test_descricao_produtos_soja(self) -> None:
        config = ConfigPipelinePAM(produtos=["40124"])
        assert config.descricao_produtos() == "soja"

    def test_descricao_produtos_milho(self) -> None:
        config = ConfigPipelinePAM(produtos=["40122"])
        assert config.descricao_produtos() == "milho"


# ---------------------------------------------------------------------------
# Testes: _dividir_em_lotes
# ---------------------------------------------------------------------------


class TestDividirEmLotes:
    """Testes para divisão de municípios em lotes."""

    def test_lista_vazia(self) -> None:
        assert _dividir_em_lotes([], 10) == []

    def test_lista_menor_que_lote(self) -> None:
        itens = [1, 2, 3]
        resultado = _dividir_em_lotes(itens, 10)
        assert resultado == [[1, 2, 3]]

    def test_lista_dividida_exatamente(self) -> None:
        itens = [1, 2, 3, 4]
        resultado = _dividir_em_lotes(itens, 2)
        assert resultado == [[1, 2], [3, 4]]

    def test_lista_com_sobra(self) -> None:
        itens = [1, 2, 3, 4, 5]
        resultado = _dividir_em_lotes(itens, 2)
        assert resultado == [[1, 2], [3, 4], [5]]

    def test_um_item_por_lote(self) -> None:
        itens = [1, 2, 3]
        resultado = _dividir_em_lotes(itens, 1)
        assert resultado == [[1], [2], [3]]

    def test_tamanho_lote_um(self) -> None:
        itens = list(range(5))
        resultado = _dividir_em_lotes(itens, 1)
        assert len(resultado) == 5
        assert all(len(lote) == 1 for lote in resultado)

    def test_tamanho_lote_invalido(self) -> None:
        with pytest.raises(ValueError, match="positivo"):
            _dividir_em_lotes([1, 2, 3], 0)
        with pytest.raises(ValueError, match="positivo"):
            _dividir_em_lotes([1, 2, 3], -1)

    def test_num_lotes_correto(self) -> None:
        itens = list(range(853))
        lotes = _dividir_em_lotes(itens, 200)
        assert len(lotes) == 5  # 853 / 200 = 4.265 → 5 lotes

    def test_todos_itens_preservados(self) -> None:
        itens = list(range(853))
        lotes = _dividir_em_lotes(itens, 200)
        itens_flat = [item for lote in lotes for item in lote]
        assert itens_flat == itens


# ---------------------------------------------------------------------------
# Testes: Nomes e caminhos de arquivo
# ---------------------------------------------------------------------------


class TestNomesArquivos:
    """Testes para geração de nomes e caminhos de arquivo."""

    def test_gerar_nome_base_padrao(self, config_padrao: ConfigPipelinePAM) -> None:
        assert _gerar_nome_base(config_padrao) == "pam_5457_2023_mg_milho_soja"

    def test_gerar_nome_base_sp(self) -> None:
        config = ConfigPipelinePAM(estado_sigla="SP", produtos=["40124"])
        assert _gerar_nome_base(config) == "pam_5457_2023_sp_soja"

    def test_caminho_raw(self, config_padrao: ConfigPipelinePAM, tmp_path: Path) -> None:
        caminho = _caminho_raw(config_padrao, tmp_path)
        assert caminho.name == "pam_5457_2023_mg_milho_soja.json"
        assert "raw" in str(caminho)
        assert "ibge" in str(caminho)
        assert "pam" in str(caminho)

    def test_caminho_parquet(self, config_padrao: ConfigPipelinePAM, tmp_path: Path) -> None:
        caminho = _caminho_parquet(config_padrao, tmp_path)
        assert caminho.name == "pam_5457_2023_mg_milho_soja.parquet"
        assert "processed" in str(caminho)

    def test_caminho_analytics(self, config_padrao: ConfigPipelinePAM, tmp_path: Path) -> None:
        caminho = _caminho_analytics(config_padrao, tmp_path)
        assert caminho.name == "pam_5457_2023_mg_milho_soja_analytics.parquet"
        assert "processed" in str(caminho)


# ---------------------------------------------------------------------------
# Testes: _obter_municipios
# ---------------------------------------------------------------------------


class TestObterMunicipios:
    """Testes para obtenção de municípios via API de localidades."""

    @patch("agrodata.pipelines.ibge.pipeline.httpx.Client")
    def test_sucesso(self, mock_client_cls: MagicMock) -> None:
        response_mock = MagicMock()
        response_mock.json.return_value = [
            {"id": 3100104, "nome": "Abadia dos Dourados"},
            {"id": 3100203, "nome": "Abaeté"},
        ]
        response_mock.raise_for_status = MagicMock()

        client_instance = MagicMock()
        client_instance.get.return_value = response_mock
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        municipios = _obter_municipios("31")

        assert len(municipios) == 2
        assert municipios[0]["id"] == "3100104"
        assert municipios[0]["nome"] == "Abadia dos Dourados"
        assert isinstance(municipios[0]["id"], str)

    @patch("agrodata.pipelines.ibge.pipeline.httpx.Client")
    def test_erro_http(self, mock_client_cls: MagicMock) -> None:
        import httpx

        response_mock = MagicMock()
        response_mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="404",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )

        client_instance = MagicMock()
        client_instance.get.return_value = response_mock
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(httpx.HTTPStatusError):
            _obter_municipios("99")


# ---------------------------------------------------------------------------
# Testes: executar_pipeline (fluxo principal)
# ---------------------------------------------------------------------------


class TestExecutarPipeline:
    """Testes para a execução do pipeline principal."""

    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_long_para_wide")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_duplicidade")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_nulos")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_schema")
    @patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_fluxo_completo(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_df: MagicMock,
        mock_schema: MagicMock,
        mock_nulos: MagicMock,
        mock_duplicidade: MagicMock,
        mock_wide: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        mock_salvar_raw: MagicMock,
        config_pequena: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        # Configurar mocks
        mock_municipios.return_value = MUNICIPIOS_FAKE

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake

        df_fake = pd.DataFrame({"col1": [1]})
        mock_df.return_value = df_fake

        resultado_schema = MagicMock()
        resultado_schema.valido = True
        mock_schema.return_value = resultado_schema

        resultado_nulos = MagicMock()
        resultado_nulos.valido = True
        mock_nulos.return_value = resultado_nulos

        resultado_duplicidade = MagicMock()
        resultado_duplicidade.valido = True
        resultado_duplicidade.duplicatas = 0
        mock_duplicidade.return_value = resultado_duplicidade

        mock_wide.return_value = pd.DataFrame({"col1": [1, 2]})

        # Caminhos mockados
        mock_raw_path.return_value = tmp_path / "raw.json"
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        # Executar
        metricas = executar_pipeline(
            config=config_pequena,
            raiz=tmp_path,
        )

        # Verificar ordem de chamadas
        mock_municipios.assert_called_once_with("31")
        assert client_instance.consultar_agregado.call_count == 2  # 3 municípios / lote 2 = 2 lotes
        mock_transform.assert_called()
        mock_df.assert_called_once()
        mock_schema.assert_called_once_with(df_fake)
        mock_nulos.assert_called_once_with(df_fake)
        mock_duplicidade.assert_called_once_with(df_fake)
        mock_wide.assert_called_once_with(df_fake)
        mock_salvar_raw.assert_called_once()

        # Verificar métricas
        assert isinstance(metricas, MetricasPipeline)
        assert metricas.num_municipios == 3
        assert metricas.num_lotes == 2
        assert metricas.config == config_pequena

    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_long_para_wide")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_duplicidade")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_nulos")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_schema")
    @patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_metricas_retornadas(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_df: MagicMock,
        mock_schema: MagicMock,
        mock_nulos: MagicMock,
        mock_duplicidade: MagicMock,
        mock_wide: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        mock_salvar_raw: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        mock_municipios.return_value = MUNICIPIOS_FAKE

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake
        mock_df.return_value = pd.DataFrame({"a": [1]})

        resultado_schema = MagicMock()
        resultado_schema.valido = True
        mock_schema.return_value = resultado_schema

        resultado_nulos = MagicMock()
        resultado_nulos.valido = True
        mock_nulos.return_value = resultado_nulos

        resultado_duplicidade = MagicMock()
        resultado_duplicidade.valido = True
        resultado_duplicidade.duplicatas = 0
        mock_duplicidade.return_value = resultado_duplicidade

        mock_wide.return_value = pd.DataFrame({"a": [1]})

        mock_raw_path.return_value = tmp_path / "raw.json"
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        metricas = executar_pipeline(config=config_padrao, raiz=tmp_path)

        assert isinstance(metricas, MetricasPipeline)
        assert metricas.num_municipios == 3
        assert metricas.num_lotes == 1  # 3 < 200 → 1 lote
        assert metricas.tamanho_lote == 200
        assert metricas.registros_transformados == 2
        assert metricas.linhas_dataframe == 1
        assert metricas.linhas_analytics == 1
        assert metricas.tempo_total_seg >= 0
        assert metricas.tempo_consulta_seg >= 0
        assert metricas.tempo_transformacao_seg >= 0
        assert metricas.tempo_quality_seg >= 0
        assert metricas.tempo_analytics_seg >= 0


# ---------------------------------------------------------------------------
# Testes: Falha de qualidade
# ---------------------------------------------------------------------------


class TestFalhaQualidade:
    """Testes para interrupção do pipeline por falha de qualidade."""

    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_falha_schema(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_salvar_raw: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        mock_municipios.return_value = MUNICIPIOS_FAKE[:1]

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake

        mock_raw_path.return_value = tmp_path / "raw.json"
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        with patch("agrodata.pipelines.ibge.pipeline.verificar_schema") as mock_schema:
            resultado = MagicMock()
            resultado.valido = False
            resultado.colunas_ausentes = ["col_faltante"]
            resultado.colunas_extras = []
            mock_schema.return_value = resultado

            with pytest.raises(RuntimeError, match="schema inválido"):
                executar_pipeline(config=config_padrao, raiz=tmp_path)

    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_falha_nulos(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_salvar_raw: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        mock_municipios.return_value = MUNICIPIOS_FAKE[:1]

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake

        mock_raw_path.return_value = tmp_path / "raw.json"
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        df_fake = pd.DataFrame({"col1": [1]})

        with (
            patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe", return_value=df_fake),
            patch("agrodata.pipelines.ibge.pipeline.verificar_schema") as mock_schema,
            patch("agrodata.pipelines.ibge.pipeline.verificar_nulos") as mock_nulos,
        ):
            s = MagicMock()
            s.valido = True
            mock_schema.return_value = s

            n = MagicMock()
            n.valido = False
            n.nulos_por_coluna = {"variavel_id": 5}
            mock_nulos.return_value = n

            with pytest.raises(RuntimeError, match="nulos em colunas obrigatórias"):
                executar_pipeline(config=config_padrao, raiz=tmp_path)

    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_falha_duplicidade(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_salvar_raw: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        mock_municipios.return_value = MUNICIPIOS_FAKE[:1]

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake

        mock_raw_path.return_value = tmp_path / "raw.json"
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        df_fake = pd.DataFrame({"col1": [1]})

        with (
            patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe", return_value=df_fake),
            patch("agrodata.pipelines.ibge.pipeline.verificar_schema") as mock_schema,
            patch("agrodata.pipelines.ibge.pipeline.verificar_nulos") as mock_nulos,
            patch("agrodata.pipelines.ibge.pipeline.verificar_duplicidade") as mock_dup,
        ):
            s = MagicMock()
            s.valido = True
            mock_schema.return_value = s

            n = MagicMock()
            n.valido = True
            mock_nulos.return_value = n

            d = MagicMock()
            d.valido = False
            d.duplicatas = 10
            mock_dup.return_value = d

            with pytest.raises(RuntimeError, match="duplicidade"):
                executar_pipeline(config=config_padrao, raiz=tmp_path)


# ---------------------------------------------------------------------------
# Testes: Comportamento com RAW existente
# ---------------------------------------------------------------------------


class TestRawExistente:
    """Testes para comportamento quando RAW já existe."""

    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_long_para_wide")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_duplicidade")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_nulos")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_schema")
    @patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    def test_reutilizar_raw_existente(
        self,
        mock_transform: MagicMock,
        mock_df: MagicMock,
        mock_schema: MagicMock,
        mock_nulos: MagicMock,
        mock_duplicidade: MagicMock,
        mock_wide: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        mock_salvar_raw: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        # Criar RAW fake
        raw_path = tmp_path / "raw.json"
        mock_raw_path.return_value = raw_path
        raw_path.write_text(json.dumps(RESPOSTA_SIDRA), encoding="utf-8")

        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        mock_transform.return_value = registros_fake
        mock_df.return_value = pd.DataFrame({"a": [1]})

        s = MagicMock()
        s.valido = True
        mock_schema.return_value = s

        n = MagicMock()
        n.valido = True
        mock_nulos.return_value = n

        d = MagicMock()
        d.valido = True
        d.duplicatas = 0
        mock_duplicidade.return_value = d

        mock_wide.return_value = pd.DataFrame({"a": [1]})

        metricas = executar_pipeline(
            config=config_padrao,
            raiz=tmp_path,
            reutilizar_raw=True,
        )

        # Não deve chamar API
        mock_salvar_raw.assert_not_called()
        assert metricas.num_municipios == 0
        assert metricas.num_lotes == 1

    def test_falha_raw_ja_existe(self, tmp_path: Path) -> None:
        raw_path = tmp_path / "raw.json"
        raw_path.write_text("[]", encoding="utf-8")

        with (
            patch("agrodata.pipelines.ibge.pipeline._caminho_raw", return_value=raw_path),
            patch("agrodata.pipelines.ibge.pipeline._caminho_parquet"),
            patch("agrodata.pipelines.ibge.pipeline._caminho_analytics"),
            pytest.raises(FileExistsError, match="já existe"),
        ):
            executar_pipeline(raiz=tmp_path, reutilizar_raw=False, permitir_sobrescrever_raw=False)

    @patch("agrodata.pipelines.ibge.pipeline._salvar_raw")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_analytics")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_parquet")
    @patch("agrodata.pipelines.ibge.pipeline._caminho_raw")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_long_para_wide")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_duplicidade")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_nulos")
    @patch("agrodata.pipelines.ibge.pipeline.verificar_schema")
    @patch("agrodata.pipelines.ibge.pipeline.registros_para_dataframe")
    @patch("agrodata.pipelines.ibge.pipeline.transformar_resposta_pam")
    @patch("agrodata.pipelines.ibge.pipeline.IBGEClient")
    @patch("agrodata.pipelines.ibge.pipeline._obter_municipios")
    def test_sobrescrever_raw(
        self,
        mock_municipios: MagicMock,
        mock_client_cls: MagicMock,
        mock_transform: MagicMock,
        mock_df: MagicMock,
        mock_schema: MagicMock,
        mock_nulos: MagicMock,
        mock_duplicidade: MagicMock,
        mock_wide: MagicMock,
        mock_raw_path: MagicMock,
        mock_parquet_path: MagicMock,
        mock_analytics_path: MagicMock,
        mock_salvar_raw: MagicMock,
        config_padrao: ConfigPipelinePAM,
        registros_fake: list[RegistroAgricola],
        tmp_path: Path,
    ) -> None:
        # Criar RAW existente
        raw_path = tmp_path / "raw.json"
        raw_path.write_text("[]", encoding="utf-8")
        mock_raw_path.return_value = raw_path

        mock_municipios.return_value = MUNICIPIOS_FAKE[:1]

        client_instance = MagicMock()
        client_instance.consultar_agregado.return_value = RESPOSTA_SIDRA
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_transform.return_value = registros_fake
        mock_df.return_value = pd.DataFrame({"a": [1]})

        s = MagicMock()
        s.valido = True
        mock_schema.return_value = s

        n = MagicMock()
        n.valido = True
        mock_nulos.return_value = n

        d = MagicMock()
        d.valido = True
        d.duplicatas = 0
        mock_duplicidade.return_value = d

        mock_wide.return_value = pd.DataFrame({"a": [1]})
        mock_parquet_path.return_value = tmp_path / "out.parquet"
        mock_analytics_path.return_value = tmp_path / "analytics.parquet"

        # Não deve falhar quando permitir_sobrescrever_raw=True
        metricas = executar_pipeline(
            config=config_padrao,
            raiz=tmp_path,
            reutilizar_raw=False,
            permitir_sobrescrever_raw=True,
        )

        assert isinstance(metricas, MetricasPipeline)
        mock_salvar_raw.assert_called_once()


# ---------------------------------------------------------------------------
# Testes: Configuração inválida
# ---------------------------------------------------------------------------


class TestConfigInvalida:
    """Testes para comportamento com configuração inválida."""

    def test_tamanho_lote_invalido(self) -> None:
        with pytest.raises(ValueError, match="positivo"):
            ConfigPipelinePAM(tamanho_lote=0)

    def test_tamanho_lote_negativo(self) -> None:
        with pytest.raises(ValueError, match="positivo"):
            ConfigPipelinePAM(tamanho_lote=-5)

    def test_lista_produtos_vazia(self) -> None:
        config = ConfigPipelinePAM(produtos=[])
        assert config.produtos == []

    def test_lista_variaveis_vazia(self) -> None:
        config = ConfigPipelinePAM(variaveis=[])
        assert config.variaveis == []


# ---------------------------------------------------------------------------
# Testes: Métricas
# ---------------------------------------------------------------------------


class TestMetricas:
    """Testes para a estrutura de métricas."""

    def test_metricas_campos(self, config_padrao: ConfigPipelinePAM) -> None:
        metricas = MetricasPipeline(
            config=config_padrao,
            num_municipios=853,
            num_lotes=5,
            tamanho_lote=200,
            registros_recebidos=6824,
            registros_transformados=6824,
            linhas_dataframe=6824,
            linhas_analytics=1137,
            tempo_total_seg=10.5,
            tempo_consulta_seg=8.0,
            tempo_transformacao_seg=0.5,
            tempo_quality_seg=0.3,
            tempo_analytics_seg=0.2,
            caminho_raw="/tmp/raw.json",
            caminho_parquet="/tmp/out.parquet",
            caminho_analytics="/tmp/analytics.parquet",
        )
        assert metricas.num_municipios == 853
        assert metricas.num_lotes == 5
        assert metricas.linhas_dataframe == 6824
        assert metricas.linhas_analytics == 1137
        assert metricas.config == config_padrao

    def test_metricas_frozen(self, config_padrao: ConfigPipelinePAM) -> None:
        metricas = MetricasPipeline(
            config=config_padrao,
            num_municipios=0,
            num_lotes=0,
            tamanho_lote=200,
            registros_recebidos=0,
            registros_transformados=0,
            linhas_dataframe=0,
            linhas_analytics=0,
            tempo_total_seg=0.0,
            tempo_consulta_seg=0.0,
            tempo_transformacao_seg=0.0,
            tempo_quality_seg=0.0,
            tempo_analytics_seg=0.0,
            caminho_raw="",
            caminho_parquet="",
            caminho_analytics="",
        )
        with pytest.raises(AttributeError):
            metricas.num_municipios = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Teste de integração: pipeline com JSON real
# ---------------------------------------------------------------------------


class TestIntegracaoPipeline:
    """Testes de integração usando fixture versionada (sem rede, sem data/raw).

    Estes testes NÃO fazem chamadas à API. Usam a fixture
    ``pam_5457_2023_amostra.json`` para validar o fluxo
    transformação → DataFrame → quality.
    """

    def test_fluxo_com_amostra(self, tmp_path: Path) -> None:
        """Testa transformação → DataFrame → quality com dados reais."""
        from agrodata.pipelines.ibge.load import registros_para_dataframe
        from agrodata.pipelines.ibge.quality import (
            verificar_duplicidade,
            verificar_nulos,
            verificar_schema,
        )
        from agrodata.pipelines.ibge.transform import transformar_resposta_pam

        # Carrega fixture versionada
        raw_path = FIXTURES_PAM_DIR / "pam_5457_2023_amostra.json"
        with raw_path.open(encoding="utf-8") as f:
            dados = json.load(f)

        # Transforma
        registros = transformar_resposta_pam(dados)
        assert len(registros) > 0

        # Cria DataFrame
        df = registros_para_dataframe(registros)
        assert len(df) > 0
        assert "variavel_id" in df.columns

        # Quality checks
        resultado_schema = verificar_schema(df)
        assert resultado_schema.valido, f"Schema inválido: {resultado_schema.colunas_ausentes}"

        resultado_nulos = verificar_nulos(df)
        assert resultado_nulos.valido, f"Nulos: {resultado_nulos.nulos_por_coluna}"

        resultado_duplicidade = verificar_duplicidade(df)
        assert resultado_duplicidade.valido, f"Duplicidades: {resultado_duplicidade.duplicatas}"
