"""Testes para a transformação da resposta SIDRA em registros achatados."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agrodata.pipelines.ibge.transform import (
    _extrair_categoria,
    _extrair_valor_numerico,
    transformar_resposta_pam,
)

# ---------------------------------------------------------------------------
# Paths para dados reais
# ---------------------------------------------------------------------------

DATA_DIR = Path("data/raw/ibge/pam")
ARQUIVO_AMOSTRA = DATA_DIR / "pam_5457_2023_amostra.json"
ARQUIVO_SP_SOJA = DATA_DIR / "pam_5457_2023_sp_soja.json"


def _carregar_json(caminho: Path) -> list[dict]:
    """Carrega JSON do disco."""
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Fixture com resposta simples (1 variável, 1 resultado, 1 série)
# ---------------------------------------------------------------------------

RESPOSTA_SIMPLES = [
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

# Resposta com múltiplos períodos
RESPOSTA_MULTI_PERIODOS = [
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
                        "serie": {"2022": "700", "2023": "790"},
                    }
                ],
            }
        ],
    }
]

# Resposta com múltiplas localidades
RESPOSTA_MULTI_LOCALIDADES = [
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
                    },
                    {
                        "localidade": {
                            "id": "3550308",
                            "nivel": {"id": "N6", "nome": "Município"},
                            "nome": "São Paulo (SP)",
                        },
                        "serie": {"2023": "-"},
                    },
                ],
            }
        ],
    }
]

# Resposta com valores especiais
RESPOSTA_VALORES_ESPECIAIS = [
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
                        "serie": {"2023": "-"},
                    }
                ],
            },
            {
                "classificacoes": [
                    {
                        "id": "782",
                        "nome": "Produto das lavouras temporárias e permanentes",
                        "categoria": {"40122": "Milho (em grão)"},
                    }
                ],
                "series": [
                    {
                        "localidade": {
                            "id": "5103403",
                            "nivel": {"id": "N6", "nome": "Município"},
                            "nome": "Cuiabá (MT)",
                        },
                        "serie": {"2023": ".."},
                    }
                ],
            },
            {
                "classificacoes": [
                    {
                        "id": "782",
                        "nome": "Produto das lavouras temporárias e permanentes",
                        "categoria": {"40123": "Arroz (em grão)"},
                    }
                ],
                "series": [
                    {
                        "localidade": {
                            "id": "5103403",
                            "nivel": {"id": "N6", "nome": "Município"},
                            "nome": "Cuiabá (MT)",
                        },
                        "serie": {"2023": "..."},
                    }
                ],
            },
        ],
    }
]

# Resposta vazia
RESPOSTA_VAZIA: list[dict] = []


# ---------------------------------------------------------------------------
# Testes: _extrair_categoria
# ---------------------------------------------------------------------------


class TestExtrairCategoria:
    """Testes para a função auxiliar _extrair_categoria."""

    def test_extrai_categoria_corretamente(self) -> None:
        classificacoes = [
            {
                "id": "782",
                "nome": "Produto das lavouras temporárias e permanentes",
                "categoria": {"40124": "Soja (em grão)"},
            }
        ]
        cid, cnome, catcodigo, catnome = _extrair_categoria(classificacoes)
        assert cid == "782"
        assert "lavouras" in cnome
        assert catcodigo == "40124"
        assert catnome == "Soja (em grão)"

    def test_extrai_milho(self) -> None:
        classificacoes = [
            {
                "id": "782",
                "nome": "Produto das lavouras temporárias e permanentes",
                "categoria": {"40122": "Milho (em grão)"},
            }
        ]
        _, _, catcodigo, catnome = _extrair_categoria(classificacoes)
        assert catcodigo == "40122"
        assert catnome == "Milho (em grão)"

    def test_primeira_classificacao_quando_multiplas(self) -> None:
        """Quando há múltiplas classificações, usa apenas a primeira."""
        classificacoes = [
            {
                "id": "782",
                "nome": "Produto",
                "categoria": {"40124": "Soja"},
            },
            {
                "id": "999",
                "nome": "Outra",
                "categoria": {"99999": "Outro"},
            },
        ]
        cid, _, catcodigo, _ = _extrair_categoria(classificacoes)
        assert cid == "782"
        assert catcodigo == "40124"


# ---------------------------------------------------------------------------
# Testes: _extrair_valor_numerico
# ---------------------------------------------------------------------------


class TestExtrairValorNumerico:
    """Testes para a função auxiliar _extrair_valor_numerico."""

    def test_valor_inteiro(self) -> None:
        assert _extrair_valor_numerico("790") == 790.0

    def test_valor_float(self) -> None:
        assert _extrair_valor_numerico("3400.5") == 3400.5

    def test_valor_menos(self) -> None:
        assert _extrair_valor_numerico("-") is None

    def test_valor_dois_pontos(self) -> None:
        assert _extrair_valor_numerico("..") is None

    def test_valor_tres_pontos(self) -> None:
        assert _extrair_valor_numerico("...") is None

    def test_valor_zero(self) -> None:
        assert _extrair_valor_numerico("0") == 0.0

    def test_valor_vazio(self) -> None:
        assert _extrair_valor_numerico("") is None

    def test_valor_nao_numerico(self) -> None:
        assert _extrair_valor_numerico("abc") is None


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — resposta simples
# ---------------------------------------------------------------------------


class TestTransformarRespostaSimples:
    """Testes com resposta de registro simples."""

    def test_gera_um_registro(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert len(registros) == 1

    def test_campos_corretos(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        r = registros[0]
        assert r.variavel_id == "8331"
        assert r.variavel_nome == "Área plantada ou destinada à colheita"
        assert r.variavel_unidade == "Hectares"
        assert r.classificacao_id == "782"
        assert r.categoria_codigo == "40124"
        assert r.categoria_nome == "Soja (em grão)"
        assert r.localidade_id == "5103403"
        assert r.localidade_nome == "Cuiabá (MT)"
        assert r.nivel_territorial_id == "N6"
        assert r.nivel_territorial_nome == "Município"
        assert r.periodo == "2023"
        assert r.valor_bruto == "790"
        assert r.valor_numerico == 790.0


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — JSON real amostra
# ---------------------------------------------------------------------------


class TestTransformarRespostaAmostra:
    """Testes com JSON real pam_5457_2023_amostra.json."""

    @pytest.fixture()
    def registros(self) -> list:
        dados = _carregar_json(ARQUIVO_AMOSTRA)
        return transformar_resposta_pam(dados)

    def test_quantidade_registros(self, registros: list) -> None:
        """4 variáveis × 2 resultados (soja + milho) = 8 registros."""
        assert len(registros) == 8

    def test_cuiaba_soja_area_plantada(self, registros: list) -> None:
        r = registros[0]
        assert r.variavel_id == "8331"
        assert r.categoria_codigo == "40124"
        assert r.categoria_nome == "Soja (em grão)"
        assert r.localidade_nome == "Cuiabá (MT)"
        assert r.valor_bruto == "790"
        assert r.valor_numerico == 790.0

    def test_cuiaba_milho_area_plantada(self, registros: list) -> None:
        r = registros[1]
        assert r.variavel_id == "8331"
        assert r.categoria_codigo == "40122"
        assert r.categoria_nome == "Milho (em grão)"
        assert r.localidade_nome == "Cuiabá (MT)"
        assert r.valor_bruto == "350"
        assert r.valor_numerico == 350.0

    def test_cuiaba_soja_quantidade_produzida(self, registros: list) -> None:
        r = registros[2]
        assert r.variavel_id == "214"
        assert r.variavel_nome == "Quantidade produzida"
        assert r.variavel_unidade == "Toneladas"
        assert r.categoria_codigo == "40124"
        assert r.valor_bruto == "2686"
        assert r.valor_numerico == 2686.0

    def test_cuiaba_milho_quantidade_produzida(self, registros: list) -> None:
        r = registros[3]
        assert r.variavel_id == "214"
        assert r.categoria_codigo == "40122"
        assert r.valor_bruto == "2135"
        assert r.valor_numerico == 2135.0

    def test_cuiaba_soja_rendimento(self, registros: list) -> None:
        r = registros[4]
        assert r.variavel_id == "112"
        assert r.variavel_nome == "Rendimento médio da produção"
        assert r.variavel_unidade == "Quilogramas por Hectare"
        assert r.categoria_codigo == "40124"
        assert r.valor_bruto == "3400"
        assert r.valor_numerico == 3400.0

    def test_cuiaba_milho_rendimento(self, registros: list) -> None:
        r = registros[5]
        assert r.variavel_id == "112"
        assert r.categoria_codigo == "40122"
        assert r.valor_bruto == "6100"
        assert r.valor_numerico == 6100.0

    def test_cuiaba_soja_valor_producao(self, registros: list) -> None:
        r = registros[6]
        assert r.variavel_id == "215"
        assert r.variavel_nome == "Valor da produção"
        assert r.variavel_unidade == "Mil Reais"
        assert r.categoria_codigo == "40124"
        assert r.valor_bruto == "6355"
        assert r.valor_numerico == 6355.0

    def test_cuiaba_milho_valor_producao(self, registros: list) -> None:
        r = registros[7]
        assert r.variavel_id == "215"
        assert r.categoria_codigo == "40122"
        assert r.valor_bruto == "1815"
        assert r.valor_numerico == 1815.0

    def test_todos_periodo_2023(self, registros: list) -> None:
        assert all(r.periodo == "2023" for r in registros)

    def test_todos_localidade_cuiaba(self, registros: list) -> None:
        assert all(r.localidade_id == "5103403" for r in registros)
        assert all(r.localidade_nome == "Cuiabá (MT)" for r in registros)

    def test_todos_nivel_municipio(self, registros: list) -> None:
        assert all(r.nivel_territorial_id == "N6" for r in registros)
        assert all(r.nivel_territorial_nome == "Município" for r in registros)


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — JSON real SP soja
# ---------------------------------------------------------------------------


class TestTransformarRespostaSpSoja:
    """Testes com JSON real pam_5457_2023_sp_soja.json."""

    @pytest.fixture()
    def registros(self) -> list:
        dados = _carregar_json(ARQUIVO_SP_SOJA)
        return transformar_resposta_pam(dados)

    def test_quantidade_registros(self, registros: list) -> None:
        """2 variáveis × 1 resultado = 2 registros."""
        assert len(registros) == 2

    def test_sp_soja_area_plantada(self, registros: list) -> None:
        r = registros[0]
        assert r.variavel_id == "8331"
        assert r.localidade_id == "3550308"
        assert r.localidade_nome == "São Paulo (SP)"
        assert r.categoria_codigo == "40124"
        assert r.categoria_nome == "Soja (em grão)"
        assert r.valor_bruto == "-"
        assert r.valor_numerico is None
        assert r.is_valor_ausente is True

    def test_sp_soja_quantidade_produzida(self, registros: list) -> None:
        r = registros[1]
        assert r.variavel_id == "214"
        assert r.localidade_nome == "São Paulo (SP)"
        assert r.valor_bruto == "-"
        assert r.valor_numerico is None


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — valores numéricos
# ---------------------------------------------------------------------------


class TestTransformarRespostaValoresNumericos:
    """Testes para conversão de valores numéricos."""

    def test_valor_inteiro(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].valor_numerico == 790.0

    def test_valor_preservado_como_string(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].valor_bruto == "790"
        assert isinstance(registros[0].valor_bruto, str)


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — valores especiais
# ---------------------------------------------------------------------------


class TestTransformarRespostaValoresEspeciais:
    """Testes para valores especiais ("-", "..", "...")."""

    @pytest.fixture()
    def registros(self) -> list:
        return transformar_resposta_pam(RESPOSTA_VALORES_ESPECIAIS)

    def test_valor_menos(self, registros: list) -> None:
        r = registros[0]
        assert r.valor_bruto == "-"
        assert r.valor_numerico is None
        assert r.is_valor_ausente is True

    def test_valor_dois_pontos(self, registros: list) -> None:
        r = registros[1]
        assert r.valor_bruto == ".."
        assert r.valor_numerico is None
        assert r.is_valor_ausente is True

    def test_valor_tres_pontos(self, registros: list) -> None:
        r = registros[2]
        assert r.valor_bruto == "..."
        assert r.valor_numerico is None
        assert r.is_valor_ausente is True


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — período
# ---------------------------------------------------------------------------


class TestTransformarRespostaPeriodo:
    """Testes para extração de período."""

    def test_periodo_um_registro(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].periodo == "2023"

    def test_multiplas_periodos(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_MULTI_PERIODOS)
        periodos = {r.periodo for r in registros}
        assert periodos == {"2022", "2023"}
        assert len(registros) == 2


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — localidade
# ---------------------------------------------------------------------------


class TestTransformarRespostaLocalidade:
    """Testes para extração de localidade."""

    def test_localidade_id(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].localidade_id == "5103403"

    def test_localidade_nome(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].localidade_nome == "Cuiabá (MT)"

    def test_nivel_territorial(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].nivel_territorial_id == "N6"
        assert registros[0].nivel_territorial_nome == "Município"

    def test_multiplas_localidades(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_MULTI_LOCALIDADES)
        ids = {r.localidade_id for r in registros}
        assert ids == {"5103403", "3550308"}
        assert len(registros) == 2


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — produto/categoria
# ---------------------------------------------------------------------------


class TestTransformarRespostaCategoria:
    """Testes para extração de produto/categoria."""

    def test_categoria_soja(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].categoria_codigo == "40124"
        assert registros[0].categoria_nome == "Soja (em grão)"

    def test_multiplas_categorias(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_VALORES_ESPECIAIS)
        codigos = {r.categoria_codigo for r in registros}
        assert codigos == {"40124", "40122", "40123"}


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — variável
# ---------------------------------------------------------------------------


class TestTransformarRespostaVariavel:
    """Testes para extração de variável."""

    def test_variavel_id(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].variavel_id == "8331"

    def test_variavel_nome(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].variavel_nome == "Área plantada ou destinada à colheita"

    def test_variavel_unidade(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert registros[0].variavel_unidade == "Hectares"

    def test_multiplas_variaveis(self) -> None:
        dados = _carregar_json(ARQUIVO_AMOSTRA)
        registros = transformar_resposta_pam(dados)
        variaveis = {r.variavel_id for r in registros}
        assert variaveis == {"8331", "214", "112", "215"}


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — resposta vazia
# ---------------------------------------------------------------------------


class TestTransformarRespostaVazia:
    """Testes para resposta vazia."""

    def test_retorna_lista_vazia(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_VAZIA)
        assert registros == []


# ---------------------------------------------------------------------------
# Testes: transformar_resposta_pam — tipagem
# ---------------------------------------------------------------------------


class TestTransformarRespostaTipagem:
    """Testes para garantir tipos corretos nos registros."""

    def test_retorna_lista(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert isinstance(registros, list)

    def test_elementos_sao_registro_agricola(self) -> None:
        from agrodata.pipelines.ibge.schemas import RegistroAgricola

        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert all(isinstance(r, RegistroAgricola) for r in registros)

    def test_valor_bruto_e_string(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        assert isinstance(registros[0].valor_bruto, str)

    def test_valor_numerico_e_float_ou_none(self) -> None:
        registros = transformar_resposta_pam(RESPOSTA_SIMPLES)
        v = registros[0].valor_numerico
        assert isinstance(v, float) or v is None
