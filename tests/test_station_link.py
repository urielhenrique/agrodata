"""Testes do link espacial INMET → município (MVP2.2). Sem internet."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from agrodata.geospatial.station_link import (
    COLUNAS_LINK,
    CRS_PROCESSAMENTO,
    atribuir_municipios,
    carregar_station_municipality,
    contar_coordenadas_invalidas,
    estacoes_para_pontos,
    executar_link_estacoes,
    reprojetar_para_processamento,
    salvar_station_municipality,
    vincular_estacoes_municipios,
)
from agrodata.pipelines.inmet.schemas import StationDimension


def _station(
    station_id: str = "A808",
    lat: float = -20.0,
    lon: float = -44.0,
    wmo: str | None = "83337",
) -> StationDimension:
    return StationDimension(
        station_id=station_id,
        wmo_id=wmo,
        name=f"ESTACAO {station_id}",
        uf="MG",
        latitude=lat,
        longitude=lon,
        altitude=800.0,
        extracted_at=datetime(2023, 1, 1, tzinfo=UTC),
        ingestion_run_id="teste",
    )


def _malha_2_municipios() -> gpd.GeoDataFrame:
    """Malha mínima: Alpha 3100104 | Beta 3100203, fronteira em lon -43.5."""
    gdf = gpd.GeoDataFrame(
        {
            "municipio_id": ["3100104", "3100203"],
            "municipio_nome": ["Alpha", "Beta"],
            "cd_uf": ["31", "31"],
            "uf": ["MG", "MG"],
            "area_km2": [100.0, 200.0],
            "geometry": [
                box(-44.5, -20.5, -43.5, -19.5),
                box(-43.5, -20.5, -42.5, -19.5),
            ],
        },
        crs=CRS_PROCESSAMENTO,
    )
    for coluna in ["municipio_id", "municipio_nome", "cd_uf"]:
        gdf[coluna] = gdf[coluna].astype("string")
    return gdf


def _malha_sobreposta() -> gpd.GeoDataFrame:
    """Dois polígonos sobrepostos para forçar ambiguous."""
    gdf = gpd.GeoDataFrame(
        {
            "municipio_id": ["3100104", "3100203"],
            "municipio_nome": ["Alpha", "Beta"],
            "cd_uf": ["31", "31"],
            "uf": ["MG", "MG"],
            "area_km2": [100.0, 100.0],
            "geometry": [
                box(-44.5, -20.5, -43.0, -19.5),
                box(-44.0, -20.5, -42.5, -19.5),
            ],
        },
        crs=CRS_PROCESSAMENTO,
    )
    for coluna in ["municipio_id", "municipio_nome", "cd_uf"]:
        gdf[coluna] = gdf[coluna].astype("string")
    return gdf


class TestPontos:
    def test_crs_inicial_4326(self) -> None:
        gdf = estacoes_para_pontos([_station()])
        assert gdf.crs.to_epsg() == 4326

    def test_reprojecao_4674(self) -> None:
        gdf = reprojetar_para_processamento(estacoes_para_pontos([_station()]))
        assert gdf.crs.to_epsg() == 4674

    def test_reprojecao_exige_4326(self) -> None:
        gdf = _malha_2_municipios().rename(columns={"municipio_id": "station_id"})
        with pytest.raises(ValueError, match="EPSG:4326"):
            reprojetar_para_processamento(gdf)


class TestAtribuicao:
    def test_ponto_dentro_matched(self) -> None:
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos([_station("A808", -20.0, -44.0)])),
            _malha_2_municipios(),
        )
        assert df.iloc[0]["status"] == "matched"
        assert df.iloc[0]["metodo"] == "within"
        assert str(df.iloc[0]["municipio_id"]) == "3100104"

    def test_ponto_fora_unmatched(self) -> None:
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos([_station("A999", -10.0, -40.0)])),
            _malha_2_municipios(),
        )
        assert df.iloc[0]["status"] == "unmatched"
        assert df.iloc[0]["metodo"] == "sem_atribuicao"
        assert pd.isna(df.iloc[0]["municipio_id"])

    def test_fronteira_sem_nearest(self) -> None:
        """Ponto sobre a fronteira: within exclui borda → unmatched, sem nearest."""
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos([_station("AB", -20.0, -43.5)])),
            _malha_2_municipios(),
        )
        assert df.iloc[0]["status"] == "unmatched"
        assert pd.isna(df.iloc[0]["municipio_id"])

    def test_ambiguo_sobreposicao(self) -> None:
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos([_station("AX", -20.0, -43.5)])),
            _malha_sobreposta(),
        )
        assert df.iloc[0]["status"] == "ambiguous"
        assert df.iloc[0]["metodo"] == "sem_atribuicao"
        assert pd.isna(df.iloc[0]["municipio_id"])

    def test_municipio_id_7_digitos_string(self) -> None:
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos([_station()])),
            _malha_2_municipios(),
        )
        assert str(df["municipio_id"].dtype) == "string"
        assert len(str(df.iloc[0]["municipio_id"])) == 7

    def test_multiplas_estacoes_mesmo_municipio(self) -> None:
        stations = [_station("A1", -20.0, -44.0), _station("A2", -20.1, -44.1)]
        df = atribuir_municipios(
            reprojetar_para_processamento(estacoes_para_pontos(stations)),
            _malha_2_municipios(),
        )
        assert len(df) == 2
        assert set(df["municipio_id"].astype(str)) == {"3100104"}
        assert set(df["status"]) == {"matched"}


class TestCoordenadasEQualidade:
    def test_coordenada_invalida_fora_do_join(self) -> None:
        stations = [_station("OK", -20.0, -44.0)]
        assert contar_coordenadas_invalidas(stations) == 0
        # NaN não passa na validação de limites
        bad = _station("OK2", -20.0, -44.0)
        object.__setattr__(bad, "latitude", float("nan"))
        assert contar_coordenadas_invalidas([bad]) == 1
        assert len(estacoes_para_pontos([bad])) == 0

    def test_malha_invalida_falha(self) -> None:
        from shapely.geometry import Polygon

        malha = _malha_2_municipios()
        malha.loc[0, "geometry"] = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        with pytest.raises(RuntimeError, match="[Vv]alidacao"):
            atribuir_municipios(
                reprojetar_para_processamento(estacoes_para_pontos([_station()])),
                malha,
            )


class TestRelatorio:
    def test_cobertura(self) -> None:
        stations = [
            _station("A1", -20.0, -44.0),
            _station("A2", -20.0, -43.0),
            _station("A3", -10.0, -40.0),
        ]
        _df, rel = vincular_estacoes_municipios(stations, _malha_2_municipios())
        assert rel.matched == 2
        assert rel.unmatched == 1
        assert rel.ambiguous == 0
        assert rel.coordenadas_invalidas == 0
        assert rel.total_estacoes == 3
        assert rel.percentual_matched == pytest.approx(66.67, abs=0.01)


class TestParquet:
    def test_roundtrip(self, tmp_path: Path) -> None:
        df, _ = vincular_estacoes_municipios([_station()], _malha_2_municipios())
        caminho = tmp_path / "part-0.parquet"
        salvar_station_municipality(df, caminho)
        lido = carregar_station_municipality(caminho)
        assert list(lido.columns) == COLUNAS_LINK
        assert len(lido) == 1
        assert lido.iloc[0]["status"] == "matched"


class TestE2E:
    def test_executar_link(self, tmp_path: Path) -> None:
        from agrodata.pipelines.inmet.load import salvar_stations

        stations = [_station("A808", -20.0, -44.0), _station("A821", -10.0, -40.0)]
        raiz = tmp_path / "processed"
        caminho_st = salvar_stations(stations, raiz)
        malha_path = tmp_path / "malha.parquet"
        _malha_2_municipios().to_parquet(malha_path, engine="pyarrow", index=False)
        saida = tmp_path / "out" / "part-0.parquet"
        df, rel = executar_link_estacoes(caminho_st, malha_path, saida, ano=2023, uf="MG")
        assert saida.exists()
        assert rel.total_estacoes == 2
        assert rel.matched == 1
        assert rel.unmatched == 1
        assert set(df["status"]) == {"matched", "unmatched"}
