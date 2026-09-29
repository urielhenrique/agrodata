"""Testes para integração geoespacial PAM × Malha Municipal."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest

from agrodata.geospatial.integrate import (
    CAMINHO_INTEGRADO,
    CHAVE_AGRICOLA,
    _validar_malha_para_integracao,
    _validar_pam_para_integracao,
    integrar_pam_com_malha,
)


def _criar_pam_fake() -> pd.DataFrame:
    """Cria um PAM analítico pequeno para testes."""
    return pd.DataFrame(
        {
            "municipio_id": ["3100104", "3100104", "3100203", "3100203"],
            "produto_codigo": ["40124", "40122", "40124", "40122"],
            "produto_nome": [
                "Soja (em grão)",
                "Milho (em grão)",
                "Soja (em grão)",
                "Milho (em grão)",
            ],
            "periodo": ["2023", "2023", "2023", "2023"],
            "area_plantada_ha": [1000.0, 500.0, 2000.0, 800.0],
            "quantidade_produzida_t": [3000.0, 2500.0, 6000.0, 4000.0],
            "rendimento_medio_kg_ha": [3000.0, 5000.0, 3000.0, 5000.0],
            "valor_producao_mil_reais": [15000.0, 12500.0, 30000.0, 20000.0],
            "municipio_nome": [
                "Abadia dos Dourados",
                "Abadia dos Dourados",
                "Abaete",
                "Abaete",
            ],
            "nivel_territorial_id": ["N6", "N6", "N6", "N6"],
            "nivel_territorial_nome": ["Município", "Município", "Município", "Município"],
        }
    )


def _criar_malha_fake() -> gpd.GeoDataFrame:
    """Cria uma malha municipal pequena para testes."""
    from shapely.geometry import Point

    return gpd.GeoDataFrame(
        {
            "municipio_id": ["3100104", "3100203", "3100302", "3100401"],
            "municipio_nome": [
                "Abadia dos Dourados",
                "Abaete",
                "Abre Campo",
                "Acaiaca",
            ],
            "cd_uf": ["31", "31", "31", "31"],
            "uf": ["MG", "MG", "MG", "MG"],
            "area_km2": [123.4, 567.8, 901.2, 345.6],
            "geometry": [
                Point(-47.0, -18.0),
                Point(-46.0, -19.0),
                Point(-45.0, -20.0),
                Point(-44.0, -21.0),
            ],
        },
        crs="EPSG:4674",
    )


class TestValidacaoMalhaParaIntegracao:
    """Testes para validação da malha antes da integração."""

    def test_malha_valida(self) -> None:
        """Malha válida deve passar sem erros."""
        malha = _criar_malha_fake()
        erros = _validar_malha_para_integracao(malha)
        assert erros == []

    def test_municipio_id_ausente(self) -> None:
        """Deve detectar municipio_id ausente."""
        malha = _criar_malha_fake().drop(columns=["municipio_id"])
        erros = _validar_malha_para_integracao(malha)
        assert any("municipio_id ausente" in e for e in erros)

    def test_municipio_id_nulo(self) -> None:
        """Deve detectar municipio_id nulo."""
        malha = _criar_malha_fake()
        malha.loc[0, "municipio_id"] = None
        erros = _validar_malha_para_integracao(malha)
        assert any("municipio_id possui nulos" in e for e in erros)

    def test_municipio_id_duplicado(self) -> None:
        """Deve detectar municipio_id duplicado."""
        malha = _criar_malha_fake()
        malha = pd.concat([malha, malha.iloc[[0]]], ignore_index=True)
        erros = _validar_malha_para_integracao(malha)
        assert any("municipio_id duplicado" in e for e in erros)

    def test_municipio_id_tamanho_invalido(self) -> None:
        """Deve detectar municipio_id com tamanho != 7."""
        malha = _criar_malha_fake()
        malha.loc[0, "municipio_id"] = "123"
        erros = _validar_malha_para_integracao(malha)
        assert any("municipio_id com tamanho != 7" in e for e in erros)

    def test_geometry_ausente(self) -> None:
        """Deve detectar geometry ausente."""
        malha = _criar_malha_fake().drop(columns=["geometry"])
        erros = _validar_malha_para_integracao(malha)
        # Drop geometry torna o objeto DataFrame comum
        assert any("GeoDataFrame" in e for e in erros)

    def test_geometry_nula(self) -> None:
        """Deve detectar geometry nula."""
        malha = _criar_malha_fake()
        malha.loc[0, "geometry"] = None
        erros = _validar_malha_para_integracao(malha)
        assert any("geometry possui nulos" in e for e in erros)

    def test_geometry_invalida(self) -> None:
        """Deve detectar geometry inválida."""
        from shapely.geometry import Polygon

        malha = _criar_malha_fake()
        # Cria um polígono inválido (self-intersecting)
        malha.loc[0, "geometry"] = Polygon(
            [(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)]
        )
        erros = _validar_malha_para_integracao(malha)
        assert any("geometry possui geometrias invalidas" in e for e in erros)

    def test_crs_ausente(self) -> None:
        """Deve detectar CRS ausente."""
        malha = _criar_malha_fake()
        malha.crs = None
        erros = _validar_malha_para_integracao(malha)
        assert any("CRS nao definido" in e for e in erros)


class TestValidacaoPamParaIntegracao:
    """Testes para validação do PAM antes da integração."""

    def test_pam_valido(self) -> None:
        """PAM válido deve passar sem erros."""
        pam = _criar_pam_fake()
        erros = _validar_pam_para_integracao(pam)
        assert erros == []

    def test_municipio_id_ausente(self) -> None:
        """Deve detectar municipio_id ausente."""
        pam = _criar_pam_fake().drop(columns=["municipio_id"])
        erros = _validar_pam_para_integracao(pam)
        assert any("municipio_id ausente" in e for e in erros)

    def test_municipio_id_nulo(self) -> None:
        """Deve detectar municipio_id nulo."""
        pam = _criar_pam_fake()
        pam.loc[0, "municipio_id"] = None
        erros = _validar_pam_para_integracao(pam)
        assert any("municipio_id possui nulos" in e for e in erros)

    def test_municipio_id_tamanho_invalido(self) -> None:
        """Deve detectar municipio_id com tamanho != 7."""
        pam = _criar_pam_fake()
        pam.loc[0, "municipio_id"] = "123"
        erros = _validar_pam_para_integracao(pam)
        assert any("municipio_id com tamanho != 7" in e for e in erros)

    def test_chave_agricola_ausente(self) -> None:
        """Deve detectar colunas da chave agrícola ausentes."""
        pam = _criar_pam_fake().drop(columns=["produto_codigo"])
        erros = _validar_pam_para_integracao(pam)
        assert any("colunas da chave agricola ausentes" in e.lower() for e in erros)

    def test_chave_agricola_duplicada(self) -> None:
        """Deve detectar chave agrícola duplicada."""
        pam = _criar_pam_fake()
        pam = pd.concat([pam, pam.iloc[[0]]], ignore_index=True)
        erros = _validar_pam_para_integracao(pam)
        assert any("Chave agricola duplicada" in e for e in erros)


class TestIntegracaoPamComMalha:
    """Testes para a integração PAM × Malha."""

    def test_integracao_basica(self) -> None:
        """Integração básica deve funcionar."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, resultado = integrar_pam_com_malha(pam, malha)

        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 4  # 4 linhas PAM
        assert resultado.linhas_pam == 4
        assert resultado.linhas_resultado == 4
        assert resultado.municipios_pam == 2  # 3100104, 3100203
        assert resultado.municipios_malha == 4
        assert resultado.municipios_pam_com_geometry == 2
        assert resultado.municipios_malha_sem_pam == 2  # 3100302, 3100401
        assert resultado.chaves_duplicadas == 0
        assert resultado.valido is True
        assert resultado.erros == []

    def test_colunas_resultado(self) -> None:
        """Resultado deve ter as colunas esperadas."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, _ = integrar_pam_com_malha(pam, malha)

        colunas_esperadas = {
            "municipio_id",
            "produto_codigo",
            "produto_nome",
            "periodo",
            "area_plantada_ha",
            "quantidade_produzida_t",
            "rendimento_medio_kg_ha",
            "valor_producao_mil_reais",
            "municipio_nome",
            "cd_uf",
            "uf",
            "area_km2",
            "geometry",
        }
        assert set(gdf.columns) == colunas_esperadas

    def test_municipio_nome_vem_da_malha(self) -> None:
        """municipio_nome deve vir da malha (autoridade territorial)."""
        pam = _criar_pam_fake()
        # Altera nome no PAM para verificar que não é usado
        pam.loc[pam["municipio_id"] == "3100104", "municipio_nome"] = "NOME ERRADO"

        malha = _criar_malha_fake()
        gdf, _ = integrar_pam_com_malha(pam, malha)

        assert gdf.loc[gdf["municipio_id"] == "3100104", "municipio_nome"].iloc[0] == "Abadia dos Dourados"

    def test_preservacao_valores_agricolas(self) -> None:
        """Valores agrícolas devem ser preservados exatamente."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, _ = integrar_pam_com_malha(pam, malha)

        # Verifica valores do primeiro registro
        row = gdf[gdf["municipio_id"] == "3100104"].iloc[0]
        assert row["area_plantada_ha"] == 1000.0
        assert row["quantidade_produzida_t"] == 3000.0
        assert row["rendimento_medio_kg_ha"] == 3000.0
        assert row["valor_producao_mil_reais"] == 15000.0

    def test_geometry_preservada(self) -> None:
        """Geometry deve ser preservada da malha."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, _ = integrar_pam_com_malha(pam, malha)

        assert gdf.geometry.crs == malha.crs
        assert not gdf.geometry.isna().any()
        assert gdf.geometry.is_valid.all()

    def test_crs_preservado(self) -> None:
        """CRS deve ser preservado."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, _ = integrar_pam_com_malha(pam, malha)

        assert gdf.crs.to_epsg() == 4674

    def test_chave_agricola_unica(self) -> None:
        """Chave agrícola deve permanecer única."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, resultado = integrar_pam_com_malha(pam, malha)

        assert resultado.chaves_duplicadas == 0
        assert gdf.duplicated(subset=CHAVE_AGRICOLA).sum() == 0

    def test_pam_sem_geometry_na_malha_falha(self) -> None:
        """Deve falhar se PAM tem municipio_id não presente na malha."""
        pam = _criar_pam_fake()
        # Adiciona municipio que não existe na malha
        pam = pd.concat(
            [
                pam,
                pd.DataFrame(
                    {
                        "municipio_id": ["9999999"],
                        "produto_codigo": ["40124"],
                        "produto_nome": ["Soja (em grão)"],
                        "periodo": ["2023"],
                        "area_plantada_ha": [100.0],
                        "quantidade_produzida_t": [300.0],
                        "rendimento_medio_kg_ha": [3000.0],
                        "valor_producao_mil_reais": [1500.0],
                    }
                ),
            ],
            ignore_index=True,
        )
        malha = _criar_malha_fake()

        with pytest.raises(RuntimeError, match="nao encontrados na malha"):
            integrar_pam_com_malha(pam, malha)

    def test_cardinalidade_preservada(self) -> None:
        """Número de linhas deve ser preservado (PAM LEFT JOIN)."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        gdf, resultado = integrar_pam_com_malha(pam, malha)

        assert resultado.linhas_resultado == resultado.linhas_pam
        assert len(gdf) == len(pam)


class TestResultadoIntegracao:
    """Testes para a estrutura ResultadoIntegracao."""

    def test_campos_obrigatorios(self) -> None:
        """Todos os campos devem estar presentes."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        _, resultado = integrar_pam_com_malha(pam, malha)

        assert isinstance(resultado.linhas_pam, int)
        assert isinstance(resultado.linhas_resultado, int)
        assert isinstance(resultado.municipios_pam, int)
        assert isinstance(resultado.municipios_malha, int)
        assert isinstance(resultado.municipios_pam_com_geometry, int)
        assert isinstance(resultado.municipios_malha_sem_pam, int)
        assert isinstance(resultado.chaves_duplicadas, int)
        assert isinstance(resultado.crs, str)
        assert isinstance(resultado.valido, bool)
        assert isinstance(resultado.erros, list)

    def test_municipios_malha_sem_pam(self) -> None:
        """Deve calcular corretamente municípios da malha sem PAM."""
        pam = _criar_pam_fake()
        malha = _criar_malha_fake()

        _, resultado = integrar_pam_com_malha(pam, malha)

        # Malha tem 4, PAM tem 2 únicos
        assert resultado.municipios_malha_sem_pam == 2


class TestExecutarIntegracao:
    """Testes para a função de alto nível executar_integracao."""

    def test_caminho_padrao_constante(self) -> None:
        """Verifica constantes de caminho."""
        assert str(CAMINHO_INTEGRADO).endswith(
            "mg_pam_2023_soja_milho.parquet"
        )