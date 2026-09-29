"""Testes para persistência GeoParquet da Malha Municipal."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from agrodata.geospatial.load import (
    CAMINHO_MALHA_PROCESSADA,
    carregar_malha_geoparquet,
    salvar_malha_geoparquet,
)


def _criar_gdf_teste() -> gpd.GeoDataFrame:
    """Cria um GeoDataFrame pequeno para testes."""
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(
        {
            "municipio_id": ["3100104", "3100203", "3100302"],
            "municipio_nome": ["Abadia dos Dourados", "Abaete", "Abre Campo"],
            "cd_uf": ["31", "31", "31"],
            "uf": ["MG", "MG", "MG"],
            "area_km2": [123.4, 567.8, 901.2],
            "geometry": [Point(-47.0, -18.0), Point(-46.0, -19.0), Point(-45.0, -20.0)],
        },
        crs="EPSG:4674",
    )
    return gdf


class TestSalvarMalhaGeoParquet:
    """Testes para salvar_malha_geoparquet."""

    def test_salvar_e_carregar(self, tmp_path: Path) -> None:
        """Testa salvamento e leitura de GeoParquet."""
        gdf = _criar_gdf_teste()
        caminho = tmp_path / "test_malha.parquet"

        caminho_salvo = salvar_malha_geoparquet(gdf, caminho)
        assert caminho_salvo == caminho.resolve()
        assert caminho.exists()

        gdf_lido = carregar_malha_geoparquet(caminho)

        assert len(gdf_lido) == 3
        assert list(gdf_lido.columns) == list(gdf.columns)
        assert gdf_lido.crs.to_epsg() == 4674
        assert gdf_lido["municipio_id"].tolist() == ["3100104", "3100203", "3100302"]
        assert gdf_lido["municipio_nome"].tolist() == [
            "Abadia dos Dourados",
            "Abaete",
            "Abre Campo",
        ]
        assert gdf_lido["uf"].tolist() == ["MG", "MG", "MG"]
        assert gdf_lido["area_km2"].tolist() == [123.4, 567.8, 901.2]
        assert not gdf_lido.geometry.isna().any()

    def test_salvar_sem_caminho_padrao(self, tmp_path: Path) -> None:
        """Testa salvamento usando caminho padrão (com tmp_path como raiz)."""
        gdf = _criar_gdf_teste()
        # Testa apenas que a função aceita caminho personalizado
        caminho = tmp_path / "malha_municipal" / "mg_municipios_2023.parquet"
        caminho_salvo = salvar_malha_geoparquet(gdf, caminho)
        assert caminho_salvo == caminho.resolve()

    def test_preservacao_geometry(self, tmp_path: Path) -> None:
        """Verifica se a geometry é preservada corretamente."""
        gdf = _criar_gdf_teste()
        caminho = tmp_path / "test.parquet"

        salvar_malha_geoparquet(gdf, caminho)
        gdf_lido = carregar_malha_geoparquet(caminho)

        assert gdf_lido.geometry.crs == gdf.geometry.crs
        for orig, lido in zip(gdf.geometry, gdf_lido.geometry):
            assert orig.equals(lido)

    def test_preservacao_crs(self, tmp_path: Path) -> None:
        """Verifica se o CRS é preservado."""
        gdf = _criar_gdf_teste()
        caminho = tmp_path / "test.parquet"

        salvar_malha_geoparquet(gdf, caminho)
        gdf_lido = carregar_malha_geoparquet(caminho)

        assert gdf_lido.crs.to_epsg() == 4674

    def test_quantidade_linhas(self, tmp_path: Path) -> None:
        """Verifica se a quantidade de linhas é preservada."""
        gdf = _criar_gdf_teste()
        caminho = tmp_path / "test.parquet"

        salvar_malha_geoparquet(gdf, caminho)
        gdf_lido = carregar_malha_geoparquet(caminho)

        assert len(gdf_lido) == len(gdf)


class TestValidacaoPreCondicoes:
    """Testes para validação de pré-condições."""

    def test_erro_nao_geodataframe(self, tmp_path: Path) -> None:
        """Deve falhar se o objeto não for GeoDataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        caminho = tmp_path / "test.parquet"

        with pytest.raises(TypeError, match="GeoDataFrame"):
            salvar_malha_geoparquet(df, caminho)

    def test_erro_geometry_ausente(self, tmp_path: Path) -> None:
        """Deve falhar se geometry estiver ausente."""
        # Passa um DataFrame comum (sem geometry) - deve falhar TypeError
        df = pd.DataFrame({"municipio_id": ["3100104"]})
        caminho = tmp_path / "test.parquet"

        with pytest.raises(TypeError, match="GeoDataFrame"):
            salvar_malha_geoparquet(df, caminho)

    def test_erro_crs_ausente(self, tmp_path: Path) -> None:
        """Deve falhar se CRS estiver ausente."""
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"municipio_id": ["3100104"], "geometry": [Point(0, 0)]}, crs=None
        )
        caminho = tmp_path / "test.parquet"

        with pytest.raises(ValueError, match="CRS"):
            salvar_malha_geoparquet(gdf, caminho)


class TestCarregarMalhaGeoParquet:
    """Testes para carregar_malha_geoparquet."""

    def test_arquivo_inexistente(self, tmp_path: Path) -> None:
        """Deve falhar se arquivo não existir."""
        caminho = tmp_path / "inexistente.parquet"

        with pytest.raises(FileNotFoundError):
            carregar_malha_geoparquet(caminho)

    def test_caminho_padrao_constante(self) -> None:
        """Verifica que a constante de caminho padrao esta correta."""
        caminho_str = str(CAMINHO_MALHA_PROCESSADA)
        assert "data" in caminho_str
        assert "processed" in caminho_str
        assert "ibge" in caminho_str
        assert "malha_municipal" in caminho_str
        assert "mg_municipios_2023.parquet" in caminho_str