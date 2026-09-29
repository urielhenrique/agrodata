"""Testes para os schemas Pydantic da API SIDRA."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agrodata.pipelines.ibge.schemas import (
    Categoria,
    Classificacao,
    Localidade,
    NivelTerritorial,
    RegistroAgricola,
)

# ---------------------------------------------------------------------------
# Dados de teste baseados em JSONs reais
# ---------------------------------------------------------------------------

DADOS_NIVEL_TERRITORIAL = {"id": "N6", "nome": "Município"}

DADOS_LOCALIDADE = {
    "id": "5103403",
    "nivel": DADOS_NIVEL_TERRITORIAL,
    "nome": "Cuiabá (MT)",
}

DADOS_CATEGORIA = {"codigo": "40124", "nome": "Soja (em grão)"}

DADOS_CLASSIFICACAO = {
    "id": "782",
    "nome": "Produto das lavouras temporárias e permanentes",
    "categorias": [DADOS_CATEGORIA],
}

DADOS_REGISTRO_COMPLETO = {
    "variavel_id": "8331",
    "variavel_nome": "Área plantada ou destinada à colheita",
    "variavel_unidade": "Hectares",
    "classificacao_id": "782",
    "classificacao_nome": "Produto das lavouras temporárias e permanentes",
    "categoria_codigo": "40124",
    "categoria_nome": "Soja (em grão)",
    "localidade_id": "5103403",
    "localidade_nome": "Cuiabá (MT)",
    "nivel_territorial_id": "N6",
    "nivel_territorial_nome": "Município",
    "periodo": "2023",
    "valor_bruto": "790",
}

DADOS_REGISTRO_VALOR_AUSENTE = {
    "variavel_id": "8331",
    "variavel_nome": "Área plantada ou destinada à colheita",
    "variavel_unidade": "Hectares",
    "classificacao_id": "782",
    "classificacao_nome": "Produto das lavouras temporárias e permanentes",
    "categoria_codigo": "40124",
    "categoria_nome": "Soja (em grão)",
    "localidade_id": "3550308",
    "localidade_nome": "São Paulo (SP)",
    "nivel_territorial_id": "N6",
    "nivel_territorial_nome": "Município",
    "periodo": "2023",
    "valor_bruto": "-",
}


# ---------------------------------------------------------------------------
# Testes: NivelTerritorial
# ---------------------------------------------------------------------------


class TestNivelTerritorial:
    """Testes para o modelo NivelTerritorial."""

    def test_criacao_basica(self) -> None:
        nivel = NivelTerritorial(**DADOS_NIVEL_TERRITORIAL)
        assert nivel.id == "N6"
        assert nivel.nome == "Município"

    def test_niveis_diversos(self) -> None:
        for nid, nome in [
            ("N1", "Brasil"),
            ("N2", "Região"),
            ("N3", "Unidade da Federação"),
            ("N6", "Município"),
        ]:
            nivel = NivelTerritorial(id=nid, nome=nome)
            assert nivel.id == nid
            assert nivel.nome == nome


# ---------------------------------------------------------------------------
# Testes: Localidade
# ---------------------------------------------------------------------------


class TestLocalidade:
    """Testes para o modelo Localidade."""

    def test_criacao_basica(self) -> None:
        localidade = Localidade(**DADOS_LOCALIDADE)
        assert localidade.id == "5103403"
        assert localidade.nome == "Cuiabá (MT)"
        assert localidade.nivel.id == "N6"
        assert localidade.nivel.nome == "Município"

    def test_localidade_sem_nivel_falha(self) -> None:
        with pytest.raises(ValidationError):
            Localidade(id="5103403", nome="Cuiabá (MT)")


# ---------------------------------------------------------------------------
# Testes: Categoria
# ---------------------------------------------------------------------------


class TestCategoria:
    """Testes para o modelo Categoria."""

    def test_criacao_basica(self) -> None:
        categoria = Categoria(**DADOS_CATEGORIA)
        assert categoria.codigo == "40124"
        assert categoria.nome == "Soja (em grão)"


# ---------------------------------------------------------------------------
# Testes: Classificacao
# ---------------------------------------------------------------------------


class TestClassificacao:
    """Testes para o modelo Classificacao."""

    def test_criacao_basica(self) -> None:
        classificacao = Classificacao(**DADOS_CLASSIFICACAO)
        assert classificacao.id == "782"
        assert len(classificacao.categorias) == 1
        assert classificacao.categorias[0].codigo == "40124"

    def test_multiplas_categorias(self) -> None:
        dados = {
            "id": "782",
            "nome": "Produto",
            "categorias": [
                {"codigo": "40124", "nome": "Soja"},
                {"codigo": "40122", "nome": "Milho"},
            ],
        }
        classificacao = Classificacao(**dados)
        assert len(classificacao.categorias) == 2


# ---------------------------------------------------------------------------
# Testes: RegistroAgricola — valor numérico
# ---------------------------------------------------------------------------


class TestRegistroAgricolaValorNumerico:
    """Testes para conversão de valor numérico no RegistroAgricola."""

    def test_valor_numerico_automatico(self) -> None:
        registro = RegistroAgricola(**DADOS_REGISTRO_COMPLETO)
        assert registro.valor_bruto == "790"
        assert registro.valor_numerico == 790.0

    def test_valor_numerico_float(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_bruto": "3400.5"}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico == 3400.5

    def test_valor_numerico_zero(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_bruto": "0"}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico == 0.0

    def test_valor_numerico_grande(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_bruto": "1000000"}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico == 1_000_000.0

    def test_valor_numerico_explicito_preservado(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_numerico": 42.5}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico == 42.5

    def test_valor_numerico_negativo(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_bruto": "-123.4"}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico == -123.4


# ---------------------------------------------------------------------------
# Testes: RegistroAgricola — valores ausentes
# ---------------------------------------------------------------------------


class TestRegistroAgricolaValoresAusentes:
    """Testes para valores ausentes no RegistroAgricola."""

    def test_valor_menos(self) -> None:
        registro = RegistroAgricola(**DADOS_REGISTRO_VALOR_AUSENTE)
        assert registro.valor_bruto == "-"
        assert registro.valor_numerico is None
        assert registro.is_valor_ausente is True

    def test_valor_dois_pontos(self) -> None:
        dados = DADOS_REGISTRO_VALOR_AUSENTE | {"valor_bruto": ".."}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico is None
        assert registro.is_valor_ausente is True

    def test_valor_tres_pontos(self) -> None:
        dados = DADOS_REGISTRO_VALOR_AUSENTE | {"valor_bruto": "..."}
        registro = RegistroAgricola(**dados)
        assert registro.valor_numerico is None
        assert registro.is_valor_ausente is True


# ---------------------------------------------------------------------------
# Testes: RegistroAgricola — campos preservados
# ---------------------------------------------------------------------------


class TestRegistroAgricolaCamposPreservados:
    """Testes para verificação de que todos os campos são preservados."""

    def test_todos_os_campos(self) -> None:
        registro = RegistroAgricola(**DADOS_REGISTRO_COMPLETO)
        assert registro.variavel_id == "8331"
        assert registro.variavel_nome == "Área plantada ou destinada à colheita"
        assert registro.variavel_unidade == "Hectares"
        assert registro.classificacao_id == "782"
        assert registro.classificacao_nome == (
            "Produto das lavouras temporárias e permanentes"
        )
        assert registro.categoria_codigo == "40124"
        assert registro.categoria_nome == "Soja (em grão)"
        assert registro.localidade_id == "5103403"
        assert registro.localidade_nome == "Cuiabá (MT)"
        assert registro.nivel_territorial_id == "N6"
        assert registro.nivel_territorial_nome == "Município"
        assert registro.periodo == "2023"
        assert registro.valor_bruto == "790"
        assert registro.valor_numerico == 790.0


# ---------------------------------------------------------------------------
# Testes: RegistroAgricola — rejeição de dados inválidos
# ---------------------------------------------------------------------------


class TestRegistroAgricolaRejeicao:
    """Testes para rejeição de dados estruturalmente inválidos."""

    def test_campo_obrigatorio_ausente(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO.copy()
        del dados["variavel_id"]
        with pytest.raises(ValidationError):
            RegistroAgricola(**dados)

    def test_localidade_sem_nivel(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {
            "localidade_id": "5103403",
            "localidade_nome": "Cuiabá (MT)",
        }
        # Remove nivel_territorial_id e nivel_territorial_nome
        del dados["nivel_territorial_id"]
        del dados["nivel_territorial_nome"]
        with pytest.raises(ValidationError):
            RegistroAgricola(**dados)

    def test_valor_bruto_vazio(self) -> None:
        dados = DADOS_REGISTRO_COMPLETO | {"valor_bruto": ""}
        registro = RegistroAgricola(**dados)
        # String vazia não está na lista de valores ausentes
        assert registro.is_valor_ausente is False
        # Não deve conseguir converter para float
        assert registro.valor_numerico is None


# ---------------------------------------------------------------------------
# Testes: Serialização
# ---------------------------------------------------------------------------


class TestRegistroAgricolaSerializacao:
    """Testes para serialização do modelo."""

    def test_para_dict(self) -> None:
        registro = RegistroAgricola(**DADOS_REGISTRO_COMPLETO)
        d = registro.model_dump()
        assert isinstance(d, dict)
        assert d["variavel_id"] == "8331"
        assert d["valor_numerico"] == 790.0

    def test_para_json(self) -> None:
        registro = RegistroAgricola(**DADOS_REGISTRO_COMPLETO)
        json_str = registro.model_dump_json()
        assert "8331" in json_str
        assert "790" in json_str


# ---------------------------------------------------------------------------
# Testes: RegistroAgricola — extraído de JSON real (pam_5457_2023_sp_soja)
# ---------------------------------------------------------------------------


class TestRegistroAgricolaDadosReais:
    """Testes com dados extraídos diretamente dos JSONs da API SIDRA."""

    def test_sp_soja_area_plantada_valor_ausente(self) -> None:
        """São Paulo - Soja: área plantada = '-' (dado ausente)."""
        registro = RegistroAgricola(
            variavel_id="8331",
            variavel_nome="Área plantada ou destinada à colheita",
            variavel_unidade="Hectares",
            classificacao_id="782",
            classificacao_nome="Produto das lavouras temporárias e permanentes",
            categoria_codigo="40124",
            categoria_nome="Soja (em grão)",
            localidade_id="3550308",
            localidade_nome="São Paulo (SP)",
            nivel_territorial_id="N6",
            nivel_territorial_nome="Município",
            periodo="2023",
            valor_bruto="-",
        )
        assert registro.valor_bruto == "-"
        assert registro.valor_numerico is None
        assert registro.is_valor_ausente is True

    def test_cuiaba_soja_quantidade_produzida(self) -> None:
        """Cuiabá - Soja: quantidade produzida = 2686."""
        registro = RegistroAgricola(
            variavel_id="214",
            variavel_nome="Quantidade produzida",
            variavel_unidade="Toneladas",
            classificacao_id="782",
            classificacao_nome="Produto das lavouras temporárias e permanentes",
            categoria_codigo="40124",
            categoria_nome="Soja (em grão)",
            localidade_id="5103403",
            localidade_nome="Cuiabá (MT)",
            nivel_territorial_id="N6",
            nivel_territorial_nome="Município",
            periodo="2023",
            valor_bruto="2686",
        )
        assert registro.valor_numerico == 2686.0
        assert registro.is_valor_ausente is False

    def test_cuiaba_milho_rendimento(self) -> None:
        """Cuiabá - Milho: rendimento médio = 6100."""
        registro = RegistroAgricola(
            variavel_id="112",
            variavel_nome="Rendimento médio da produção",
            variavel_unidade="Quilogramas por Hectare",
            classificacao_id="782",
            classificacao_nome="Produto das lavouras temporárias e permanentes",
            categoria_codigo="40122",
            categoria_nome="Milho (em grão)",
            localidade_id="5103403",
            localidade_nome="Cuiabá (MT)",
            nivel_territorial_id="N6",
            nivel_territorial_nome="Município",
            periodo="2023",
            valor_bruto="6100",
        )
        assert registro.valor_numerico == 6100.0
        assert registro.categoria_codigo == "40122"
        assert registro.categoria_nome == "Milho (em grão)"
