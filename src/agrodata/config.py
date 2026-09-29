"""Configuração centralizada dos datasets do AgroData."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar


class DatasetConfig:
    """Caminhos e metadados dos datasets processados."""

    # Raiz do projeto (diretório que contém pyproject.toml)
    RAIZ_PROJETO = Path(__file__).resolve().parents[2]

    # Datasets processados
    PAM_INTEGRADO = RAIZ_PROJETO / "data" / "processed" / "ibge" / "malha_municipal" / "mg_pam_2023_soja_milho.parquet"
    MALHA_TERRITORIAL = RAIZ_PROJETO / "data" / "processed" / "ibge" / "malha_municipal" / "mg_municipios_2023.parquet"

    # Metadados de origem (para data lineage)
    METADADOS_ORIGEM: ClassVar[dict] = {
        "pam_analitico": {
            "fonte": "IBGE PAM 2023",
            "descricao": "Pesquisa Agrícola Municipal - Soja e Milho, Minas Gerais, 2023",
            "dataset_bruto": "pam_5457_2023_mg_soja_milho_analytics.parquet",
            "url": "https://sidra.ibge.gov.br/tabela/5457",
        },
        "malha_municipal": {
            "fonte": "IBGE Malha Municipal 2023",
            "descricao": "Limites municipais de Minas Gerais",
            "dataset_bruto": "MG_Municipios_2023.zip",
            "url": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2023/UFs/MG/MG_Municipios_2023.zip",
        },
    }

    # Colunas e constantes do domínio
    COLUNA_MUNICIPIO_ID = "municipio_id"
    COLUNA_PRODUTO_CODIGO = "produto_codigo"
    COLUNA_PRODUTO_NOME = "produto_nome"
    COLUNA_PERIODO = "periodo"
    COLUNA_AREA = "area_plantada_ha"
    COLUNA_PRODUCAO = "quantidade_produzida_t"
    COLUNA_PRODUTIVIDADE = "rendimento_medio_kg_ha"
    COLUNA_VALOR_MIL_REAIS = "valor_producao_mil_reais"
    COLUNA_GEOMETRY = "geometry"
    COLUNA_MUNICIPIO_NOME = "municipio_nome"
    COLUNA_UF = "uf"
    COLUNA_CD_UF = "cd_uf"
    COLUNA_AREA_KM2 = "area_km2"

    # Produtos válidos
    PRODUTOS_VALIDOS: ClassVar[dict] = {
        "Todos": None,
        "Soja": "Soja (em grão)",
        "Milho": "Milho (em grão)",
    }

    # Mapeamento de indicadores para colunas
    INDICADORES: ClassVar[dict] = {
        "Produção": "quantidade_produzida_t",
        "Área": "area_plantada_ha",
        "Produtividade": "rendimento_medio_kg_ha",
        "Valor da produção": "valor_producao_mil_reais",
    }

    # Período disponível
    PERIODOS_DISPONIVEIS: ClassVar[list[str]] = ["2023"]

    @classmethod
    def validar_arquivos_existem(cls) -> None:
        """Valida que os arquivos de dados existem."""
        for nome, caminho in [("PAM Integrado", cls.PAM_INTEGRADO), ("Malha Territorial", cls.MALHA_TERRITORIAL)]:
            if not caminho.exists():
                raise FileNotFoundError(f"Dataset {nome} não encontrado: {caminho}")

    @classmethod
    def obter_metadados_linhagem(cls) -> dict:
        """Retorna metadados de linhagem para exibição no dashboard."""
        return {
            "dados_agricolas": cls.METADADOS_ORIGEM["pam_analitico"],
            "geometria": cls.METADADOS_ORIGEM["malha_municipal"],
        }

    @classmethod
    def obter_dataset_hash(cls) -> str:
        """Calcula hash do dataset baseado nos arquivos de origem.

        Usa mtime dos arquivos parquet para detectar mudanças.
        Retorna string curta (primeiros 12 chars) para usar como chave de cache.
        """
        cls.validar_arquivos_existem()

        hasher = hashlib.md5()
        for caminho in [cls.PAM_INTEGRADO, cls.MALHA_TERRITORIAL]:
            stat = caminho.stat()
            hasher.update(str(stat.st_mtime_ns).encode())
            hasher.update(str(stat.st_size).encode())

        return hasher.hexdigest()[:12]