"""Schemas Pydantic para dados da API SIDRA do IBGE (tabela 5457)."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

# Valores que indicam dado ausente ou inibido conforme documentação do IBGE.
# A API retorna "-", ".." ou "..." quando o dado não está disponível,
# foi suprimido por privacidade, ou não se aplica.
VALORES_AUSENTES = frozenset({"-", "..", "..."})


class NivelTerritorial(BaseModel):
    """Nível territorial geográfico do IBGE.

    Observado diretamente no JSON:
        "nivel": {"id": "N6", "nome": "Município"}
    """

    id: str = Field(..., description="Código do nível territorial (ex: N1, N6)")
    nome: str = Field(..., description="Nome do nível territorial (ex: Município)")


class Localidade(BaseModel):
    """Localidade geográfica retornada pela API.

    Observado diretamente no JSON:
        "localidade": {"id": "5103403", "nivel": {...}, "nome": "Cuiabá (MT)"}
    """

    id: str = Field(..., description="Código da localidade (ex: 5103403)")
    nivel: NivelTerritorial = Field(..., description="Nível territorial")
    nome: str = Field(..., description="Nome da localidade com UF (ex: Cuiabá (MT))")


class Categoria(BaseModel):
    """Categoria dentro de uma classificação (ex: produto).

    Observado diretamente no JSON:
        "categoria": {"40124": "Soja (em grão)"}

    A API retorna um dict com um único par código→nome.
    Este modelo representa um único par extraído desse dict.
    """

    codigo: str = Field(..., description="Código da categoria (ex: 40124)")
    nome: str = Field(..., description="Nome da categoria (ex: Soja (em grão))")


class Classificacao(BaseModel):
    """Classificação aplicada aos dados (ex: tipo de produto).

    Observado diretamente no JSON:
        {
            "id": "782",
            "nome": "Produto das lavouras temporárias e permanentes",
            "categoria": {"40124": "Soja (em grão)"}
        }

    No contexto achatado, categorias é uma lista para suportar
    múltiplas categorias quando a consulta as seleciona.
    """

    id: str = Field(..., description="Código da classificação (ex: 782)")
    nome: str = Field(..., description="Nome da classificação")
    categorias: list[Categoria] = Field(
        ..., description="Categorias selecionadas nesta classificação"
    )


class RegistroAgricola(BaseModel):
    """Registro agrícola achatado derivado da resposta da API SIDRA.

    Representa uma única observação: valor de uma variável para uma
    combinação de localidade, período e classificação/categoria.

    Campos derivados diretamente da estrutura JSON:
        - variavel_id, variavel_nome, variavel_unidade  ← "id", "variavel", "unidade"
        - classificacao_id, classificacao_nome          ← "classificacoes[0].id/nome"
        - categoria_codigo, categoria_nome              ← "classificacoes[0].categoria"
        - localidade_id, localidade_nome                ← "series[0].localidade"
        - nivel_territorial_id, nivel_territorial_nome  ← "series[0].localidade.nivel"
        - periodo                                       ← chave de "serie"
        - valor_bruto                                   ← valor de "serie"

    Campo derivado por computação (não-existente na API):
        - valor_numerico  ← float(valor_bruto) quando possível
    """

    # --- Identificação da variável ---
    variavel_id: str = Field(..., description="Código da variável (ex: 8331)")
    variavel_nome: str = Field(
        ..., description="Nome da variável (ex: Área plantada ou destinada à colheita)"
    )
    variavel_unidade: str = Field(
        ..., description="Unidade de medida (ex: Hectares)"
    )

    # --- Identificação da classificação/categoria ---
    classificacao_id: str = Field(
        ..., description="Código da classificação (ex: 782)"
    )
    classificacao_nome: str = Field(
        ..., description="Nome da classificação"
    )
    categoria_codigo: str = Field(
        ..., description="Código da categoria/produto (ex: 40124)"
    )
    categoria_nome: str = Field(
        ..., description="Nome da categoria/produto (ex: Soja (em grão))"
    )

    # --- Identificação da localidade ---
    localidade_id: str = Field(
        ..., description="Código da localidade (ex: 5103403)"
    )
    localidade_nome: str = Field(
        ..., description="Nome da localidade (ex: Cuiabá (MT))"
    )
    nivel_territorial_id: str = Field(
        ..., description="Código do nível territorial (ex: N6)"
    )
    nivel_territorial_nome: str = Field(
        ..., description="Nome do nível territorial (ex: Município)"
    )

    # --- Período e valor ---
    periodo: str = Field(..., description="Período do dado (ex: 2023)")
    valor_bruto: str = Field(
        ..., description="Valor bruto recebido da API como string"
    )
    valor_numerico: float | None = Field(
        default=None,
        description=(
            "Valor convertido para float quando possível; "
            "None para valores ausentes ('-', '..', '...')"
        ),
    )

    @model_validator(mode="after")
    def _computar_valor_numerico(self) -> RegistroAgricola:
        """Computa valor_numerico a partir de valor_bruto quando não fornecido.

        Se valor_numerico já foi fornecido explicitamente, preserva o valor.
        Se valor_bruto é um valor ausente (VALORES_AUSENTES), mantém None.
        Caso contrário, tenta converter para float.
        """
        if self.valor_numerico is None and not self.is_valor_ausente:
            try:
                object.__setattr__(self, "valor_numerico", float(self.valor_bruto))
            except (ValueError, TypeError):
                pass
        return self

    @property
    def is_valor_ausente(self) -> bool:
        """Verifica se o valor bruto indica dado ausente."""
        return self.valor_bruto in VALORES_AUSENTES
