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

---

## INMET BDMEP — MVP2.1 (Minas Gerais, 2023)

### A. Fonte oficial
- Fonte: INMET / BDMEP (dados históricos).
- URL do ano implementado: https://portal.inmet.gov.br/dadoshistoricos/2023/BDMEP_2023.zip
- Formato: um ZIP anual contendo um CSV por estação.
- CSV: encoding `latin-1`, separador `;`, decimal `,`, header de 8 linhas (7 de metadados + 1 de cabeçalho).
- Missing da fonte (`-9999`, vazio, `NaN`) é convertido para `None`/`null`, nunca para zero.

### Estrutura dos CSVs (8 linhas de metadados + dados)
| Linha | Conteúdo |
|-------|----------|
| 1 | Região;Sudeste |
| 2 | UF;MG |
| 3 | Estação;NOME DA ESTAÇÃO |
| 4 | Código (WMO);CÓDIGO_WMO |
| 5 | Latitude;-19,92 |
| 6 | Longitude;-43,93 |
| 7 | Altitude;852,0 |
| 8 | Data;Hora UTC;PRECIPITAÇÃO...;TEMPERATURA MÁXIMA...;TEMPERATURA MÍNIMA... |

### B. Escopo implementado
- Ano: 2023 (parâmetro `ano` aceita 2000–2030, escopo validado em 2023).
- UF: MG (parâmetro `uf`, filtro por metadata do CSV).
- Observações horárias.
- Variáveis (códigos internos): `precipitacao`, `temp_max`, `temp_min`.
- Catálogo de estações a partir do header do CSV.
- Pipeline executável localmente e com fixtures ZIP locais nos testes (sem internet).

### C. RAW
- Localização lógica: `data/raw/inmet/{ano}/BDMEP_{ano}.zip` (ex.: `data/raw/inmet/2023/BDMEP_2023.zip`).
- CSVs extraídos em `data/raw/inmet/{ano}/extracted/` apenas como área temporária de trabalho.
- RAW tratado como fonte imutável: reutilizado via `reutilizar_raw`, sobrescrito somente com `permitir_sobrescrever_raw=True`.
- Download com retry/timeout/streaming (`INMETClient`).
- Dados brutos **não** são versionados no Git.

### D. Processed
- `data/processed/inmet/observations_hourly/year={ano}/uf={UF}/part-0.parquet`
- `data/processed/inmet/stations/stations.parquet`
- Formato Parquet (PyArrow, `snappy`).
- `datetime` e `extracted_at` como `timestamp[us, tz=UTC]`; `value` como `float64` nullable (`null` = missing).
- Particionamento físico: `year=` / `uf=`.
- Sem ordenação garantida antes da escrita.

#### Observações horárias (`observations_hourly`)
| Campo | Tipo | Descrição |
|-------|------|-----------|
| station_id | utf8 | Código INMET (ex: A808) — PK parte 1 |
| datetime | timestamp[us, tz=UTC] | Timestamp horário UTC — PK parte 2 |
| variable | utf8 | Enum: precipitacao, temp_max, temp_min — PK parte 3 |
| value | float64 | Valor medido (null = missing) |
| source | utf8 | Constante "INMET_BDMEP" |
| extracted_at | timestamp[us, tz=UTC] | Momento da extração |
| raw_row_hash | utf8 | SHA256 da linha bruta do CSV |
| ingestion_run_id | utf8 | UUID da execução do pipeline |
| quality_flag | utf8 | valid/missing/out_of_range/suspect |

#### Dimensão de estações (`stations`)
| Campo | Tipo |
|-------|------|
| station_id | utf8 (PK) |
| wmo_id | utf8 |
| name | utf8 |
| uf | utf8 |
| latitude | float64 |
| longitude | float64 |
| altitude | float64 |
| data_inicio | timestamp[us, tz=UTC] |
| data_fim | timestamp[us, tz=UTC] |
| source | utf8 |
| extracted_at | timestamp[us, tz=UTC] |
| ingestion_run_id | utf8 |

### E. Lineage
- `source`: origem fixa `"INMET_BDMEP"`.
- `extracted_at`: quando a execução ocorreu.
- `raw_row_hash`: SHA256 da linha original do CSV (bytes `latin-1`, antes de qualquer conversão), permitindo rastrear/dedup por linha fonte.
- `ingestion_run_id`: UUID por execução do pipeline.

### F. Qualidade (8 regras)
| # | Regra | Severidade real no código | Ação |
|---|-------|---------------------------|------|
| 1 | Missing (`-9999`/vazio) | Info (contagem) | `value=None`, `quality_flag="missing"`, registro mantido |
| 2 | Precipitação < 0 | Warning | `quality_flag="out_of_range"` |
| 3 | `temp_max < temp_min` (mesma estação+datetime) | Warning | contabilizado, não bloqueia |
| 4 | Temperatura fora de [-50, 60] | **Error/bloqueante** | `quality_flag="out_of_range"`, `valido=False` |
| 5 | Precipitação > 500 mm/h | Warning | `quality_flag="suspect"` |
| 6 | Duplicidade da chave lógica | **Error/bloqueante** | `valido=False` |
| 7 | Gap temporal > 24h | Info/Warning (contagem) | relatório apenas |
| 8 | Estação sem metadata | Warning (contagem) | relatório apenas |

**Política real:** somente errors (regras 4 e 6, `erros = duplicidade_pk + temperatura_fora_faixa`) tornam `QualityReport.valido=False`. Quando inválido, `executar_pipeline` lança `RuntimeError` **antes** da persistência; nenhum Parquet válido da execução é produzido. Warnings/infos não interrompem.

### G. Chave lógica
- `(station_id, datetime, variable)`.
- Duplicidade é detectada por `drop_duplicates` sobre essa chave.
- Duplicatas **não** são removidas automaticamente; a execução é bloqueada.

### H. Timezone
- Fonte: coluna `Hora UTC` + `Data`, interpretada como UTC (`pd.to_datetime(..., utc=True)`).
- Registros Pydantic e DataFrame mantêm datetime timezone-aware UTC.
- Parquet usa `timestamp[us, tz=UTC]`.
- Teste E2E (`test_timezone_utc_roundtrip`) garante `2023-01-01/1200` → `2023-01-01T12:00:00+00:00` no round-trip.
- Não há validação independente do relógio da fonte além do nome da coluna.

### Módulos implementados
- `src/agrodata/pipelines/inmet/client.py` — Download HTTP com retry/timeout/streaming
- `src/agrodata/pipelines/inmet/schemas.py` — Pydantic models
- `src/agrodata/pipelines/inmet/parser.py` — Leitura ZIP/CSV latin-1/`;`/decimal `,`/header 8
- `src/agrodata/pipelines/inmet/transform.py` — Normalização + validação de faixas
- `src/agrodata/pipelines/inmet/quality.py` — 8 regras + QualityReport
- `src/agrodata/pipelines/inmet/load.py` — PyArrow Parquet particionado
- `src/agrodata/pipelines/inmet/pipeline.py` — Orquestração + bloqueio em quality inválido
- `src/agrodata/pipelines/inmet/station_catalog.py` — Metadata + filtro UF

### I. Testes
- Total do projeto: **415 passed** (`pytest -q`).
- Específicos INMET: **73 passed** (`pytest tests/ -k inmet -q`).
- Integração/E2E INMET (`tests/test_inmet_integration.py`): **5 testes** — pipeline válido com 2 estações, round-trip Parquet, bloqueio por duplicidade, round-trip timezone UTC, determinismo de `raw_row_hash`.
- Fixtures pequenas em `tests/` (CSVs inline de 1–2 estações), sem ZIP anual completo no repositório.
- Ruff: `ruff check .` → **All checks passed**.

### J. Limitações do MVP2.1 (não incluído)
- Backfill completo 2000–2026 (só 2023 validado).
- Múltiplas UFs simultâneas em produção.
- Interpolação espacial.
- Agregação/join estação → município IBGE.
- Dashboard climático.
- ML.
- Airflow/Prefect.
- Banco de dados/PostGIS.
- Variáveis além de `precipitacao`, `temp_max`, `temp_min`.
- SCD2 em `stations`.

### K. Próxima etapa
- MVP2.2 previsto: integração espacial estação → município (não implementada neste MVP).