# Fontes de Dados — AgroData

## IBGE Malha Municipal 2023 — Minas Gerais

**Fonte oficial:**
https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2023/UFs/MG/MG_Municipios_2023.zip

### Características confirmadas
- 853 municípios
- CD_MUN único
- CD_MUN com 7 dígitos
- Geometrias não nulas
- Geometrias válidas
- CRS EPSG:4674
- Formato original: Shapefile dentro de ZIP

### Campos utilizados
| Campo original | Descrição |
|----------------|-----------|
| CD_MUN | Código do município (7 dígitos) |
| NM_MUN | Nome do município |
| CD_UF | Código da UF |
| AREA_KM2 | Área em km² |
| geometry | Geometria do município |

### Normalização
| Campo original | Campo normalizado | Observação |
|----------------|-------------------|------------|
| CD_MUN | municipio_id | string, 7 dígitos |
| NM_MUN | municipio_nome | string |
| CD_UF | cd_uf | string |
| — | uf | "MG", derivado do contexto da malha estadual |
| AREA_KM2 | area_km2 | float64 |
| geometry | geometry | preservada |

### GeoParquet territorial
**Caminho:** `data/processed/ibge/malha_municipal/mg_municipios_2023.parquet`

**Características:**
- 853 linhas
- geometry preservada
- CRS EPSG:4674

---

## PAM 2023 — Minas Gerais (Soja e Milho)

### Dataset analítico
**Caminho:** `data/processed/ibge/pam/pam_5457_2023_mg_soja_milho_analytics.parquet`

**Características:**
- 1.137 observações
- 847 municípios
- 2 produtos
- Período: 2023
- municipio_id com 7 dígitos

### Produtos
| Código | Nome |
|--------|------|
| 40122 | Milho (em grão) |
| 40124 | Soja (em grão) |

---

## Integração PAM × Malha Municipal

### Módulo
`src/agrodata/geospatial/integrate.py`

### Estratégia
**PAM LEFT JOIN Malha** pela chave `municipio_id`

**Motivo:**
- PAM é a fonte das observações agrícolas (preserva todas as observações existentes)
- Malha é a referência territorial (fornece geometria e atributos territoriais)

### Resultado
**Caminho:** `data/processed/ibge/malha_municipal/mg_pam_2023_soja_milho.parquet`

**Características:**
- 1.137 linhas
- 847 municípios
- 13 colunas
- geometry
- CRS EPSG:4674

### Atributos territoriais (vêm da malha)
| Campo | Origem |
|-------|--------|
| municipio_nome | Malha |
| cd_uf | Malha |
| uf | Malha |
| area_km2 | Malha |
| geometry | Malha |

### Atributos agrícolas (vêm do PAM)
| Campo | Origem |
|-------|--------|
| produto_codigo | PAM |
| produto_nome | PAM |
| periodo | PAM |
| area_plantada_ha | PAM |
| quantidade_produzida_t | PAM |
| rendimento_medio_kg_ha | PAM |
| valor_producao_mil_reais | PAM |

---

## Municípios sem PAM

A malha possui **853 municípios** e o PAM analítico possui **847 municípios**.

Existem **6 municípios** da malha que não aparecem no dataset PAM analítico.

### Tratamento
- Isso **não é tratado como erro**
- Não são criadas observações agrícolas fictícias para os 6 municípios
- Valores ausentes **não são convertidos para zero**
- Os 6 municípios continuam disponíveis no GeoParquet territorial completo (`mg_municipios_2023.parquet`)

> **Nota:** Não se afirma que esses municípios não produzem soja ou milho. Apenas não estão presentes no dataset analítico utilizado.

---

## Arquitetura: Duas Camadas

O projeto mantém duas camadas distintas com granularidades diferentes:

### 1. GeoParquet Territorial Completo
- **Arquivo:** `mg_municipios_2023.parquet`
- **Granularidade:** 1 linha por município
- **Total:** 853 municípios
- **Uso:** Referência territorial, joins futuros, visualização de limites

### 2. Dataset Agrícola Geoespacial
- **Arquivo:** `mg_pam_2023_soja_milho.parquet`
- **Granularidade:** 1 linha por `municipio_id + produto_codigo + periodo`
- **Total:** 1.137 observações (847 municípios × 2 produtos)
- **Uso:** Análise agrícola com geometria associada

---

## Qualidade

### Testes
- **308 testes passando** (281 PAM + 10 load + 27 integração)
- Cobertura: ingestão, validação, normalização, persistência, integração

### Ruff
- **Zero erros** — código em conformidade

### Validações implementadas
| Validação | Onde |
|-----------|------|
| Geometria não nula | ingest/validate/integrate |
| Geometria válida (sem buffer(0)) | validate/integrate |
| CRS EPSG:4674 | validate/integrate |
| municipio_id único | validate/integrate |
| municipio_id não nulo | validate/integrate |
| municipio_id 7 dígitos | validate/integrate |
| Cardinalidade do join preservada | integrate |
| Cobertura PAM × Malha | integrate |
| Chave agrícola única (municipio_id + produto_codigo + periodo) | integrate |
| Valores agrícolas preservados | integrate |

---

## Pipeline de Projeção e Simplificação (MVP 1)

### CRS dos Dados vs. CRS do Mapa
- **Dados analíticos (GeoParquet)**: permanecem em **EPSG:4674** (SIRGAS 2000) — fonte de verdade
- **Entrega ao mapa (API GeoJSON)**: reprojetado para **EPSG:4326** (WGS84) — apenas na borda de visualização

### Ordem de Operações
1. **Reprojeção**: EPSG:4674 → EPSG:4326 (via `GeoDataFrame.to_crs`)
2. **Simplificação**: Douglas-Peucker com tolerância **0.0005°** (≈ 55 metros no equador)

### Tolerância de Simplificação
- **Valor efetivo**: **0.0005 graus**
- Aplicada via `_simplificar_geometria_para_mapa` (chamada por `_preparar_geodataframe_para_mapa`)
- Preserva topologia: `preserve_topology=False` (mais rápido, geometrias permanecem válidas)
- Geometrias inválidas pós-simplificação são corrigidas com `buffer(0)` pontual

### Princípios
- Simplificação é **exclusivamente para apresentação cartográfica**
- **GeoParquet original NÃO é modificado** — operações ocorrem em cópia na memória
- Dados analíticos mantêm precisão total em EPSG:4674

---

## Fingerprint do Dataset

### Método
- Baseado em **mtime_ns + tamanho (bytes)** dos arquivos Parquet de origem:
  - `mg_pam_2023_soja_milho.parquet`
  - `mg_municipios_2023.parquet`
- Hash MD5 truncado a 12 caracteres (ex: `1613028bf963`)
- Implementado em `DatasetConfig.obter_dataset_hash()` (`src/agrodata/config.py:85-98`)

### Uso na Chave de Cache
- Chave composta: `{dataset_hash}:{cultura}:{periodo}:{indicador}`
- Exemplo: `1613028bf963:Todos:2023:Produção`
- Mudança nos arquivos de origem → hash diferente → invalidação automática do cache

### Limitações
- **Não é hash criptográfico do conteúdo** — detecta mudança de arquivo (mtime/size), não necessariamente mudança semântica dos dados
- Touch no arquivo (mesmo conteúdo) invalida cache
- Adequado para pipeline controlado onde arquivos só mudam via ETL versionado

---

## Cache GeoJSON (LRU em Memória)

### Implementação
- Classe `LRUCache` customizada (`src/agrodata/analytics/queries.py:22-47`)
- `maxsize = 64` entradas
- Armazena **dict GeoJSON já construído** (evita reconstrução + serialização repetida)
- Chave: `{dataset_hash}:{cultura}:{periodo}:{indicador}`

### Comportamento
| Cenário | Comportamento |
|---------|---------------|
| **Cache MISS** (primeira chamada / parâmetros novos) | Processamento completo: filtro → agregação → reprojeção → simplificação → GeoJSON (~2-6s) |
| **Cache HIT** (mesmos parâmetros) | Retorno imediato do dict em memória (~0.16s HTTP) |
| **Restart do processo** | **Cache perdido** — primeira chamada será MISS |
| **Múltiplos workers/instâncias** | **Não compartilhado** — cada processo tem seu cache independente |
| **Mudança de cultura/indicador/período** | Chave diferente → MISS (processa nova combinação) |

### O que o Cache Evita
- Filtro por cultura/período
- Agregação municipal (para "Todos")
- Reprojeção EPSG:4674 → EPSG:4326
- Simplificação de geometrias (0.0005°)
- Construção do dict GeoJSON (`__geo_interface__`)

### O que o Cache NÃO Evita
- Serialização JSON na resposta HTTP (FastAPI → Pydantic → JSON)
- Transferência de rede (~10.45 MB para "Todos/Produção")

### Performance Observada (MVP 1)
- **MISS médio**: ~3.3s (varia 1.6-6.2s conforme combinação)
- **HIT médio**: ~0.16s
- **Speedup**: ~20x
- **GeoJSON "Todos/Produção"**: 847 features, 10.45 MB
- **GeoJSON "Milho/Produção"**: 847 features
- **GeoJSON "Soja/Produção"**: 290 features