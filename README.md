# AgroData

**Open data infrastructure for reproducible agricultural intelligence in Brazil**

---

## Visão Geral

O AgroData é uma plataforma de engenharia de dados geoespaciais focada em transformar dados públicos agrícolas brasileiros em inteligência territorial reproduzível. O projeto nasce como aprendizado e portfolio, evoluindo incrementalmente de um pipeline de dados simples para uma plataforma geoespacial profissional.

**MVP 1 (atual)**: Integração IBGE PAM 2023 (Soja e Milho) + Malha Municipal MG 2023 com API FastAPI e dashboard Streamlit.

---

## Problema

Dados agrícolas públicos no Brasil (IBGE PAM, CONAB, INMET, MapBiomas, etc.) são:

- Fragmentados em múltiplas fontes e formatos
- Difíceis de integrar com geometrias territoriais
- Frequentemente usados sem rastreabilidade de transformações
- Pouco acessíveis para análise geoespacial reproduzível

O AgroData resolve isso provendo:

- Pipelines versionados e testados de ingestão → processamento → análise
- GeoParquet como formato de intercâmbio (preserva geometria, CRS, tipos)
- CRS único no processamento (EPSG:4674/SIRGAS 2000) com reprojeção apenas na borda de visualização
- Cache inteligente para consultas geoespaciais repetidas
- API REST + dashboard interativo para consumo

---

## Estado Atual

| Componente | Status |
|------------|--------|
| **Pipeline IBGE PAM** | ✅ Completo (ingestão, validação, transformação, integração com malha) |
| **GeoParquet processados** | ✅ 2 datasets: malha territorial (853 municípios) + PAM integrado (1.137 observações) |
| **API FastAPI** | ✅ 6 endpoints: `/map/geojson`, `/kpis`, `/ranking`, `/municipality`, `/insights`, `/scatter` |
| **Dashboard Streamlit** | ✅ Mapa coroplético, KPIs, ranking, scatter, detalhe de município, insights |
| **Cache LRU** | ✅ Em memória, maxsize=64, chave por dataset_hash + filtros |
| **Testes** | ✅ 342 testes passando (unitários + integração) |
| **Qualidade** | ✅ Ruff clean, type hints, validações de geometria/CRS/cardinalidade |

**Métricas de performance (MVP 1):**
- Cache MISS: ~0.3–6s (processamento geoespacial completo)
- Cache HIT: ~0.16s (serialização HTTP)
- GeoJSON "Todos/Produção": 847 features, ~10.5 MB
- Speedup médio: ~20x

---

## Principais Tecnologias

| Camada | Tecnologias |
|--------|-------------|
| **Linguagem** | Python 3.13 |
| **Dados geoespaciais** | GeoPandas, PyArrow, Shapely, PyProj |
| **API** | FastAPI, Uvicorn, Pydantic |
| **Dashboard** | Streamlit, Streamlit-Folium, Folium, Plotly |
| **Testes** | pytest |
| **Lint/Format** | Ruff |
| **Dados** | GeoParquet, IBGE SIDRA API, Malha Municipal IBGE |

---

## Arquitetura Atual

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Fontes IBGE   │────▶│  Pipeline ETL    │────▶│   GeoParquet        │
│  PAM + Malha    │     │  (validado,      │     │  (EPSG:4674,        │
│  (raw, imutável)│     │   versionado)    │     │   particionado)     │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                             │
                        ┌────────────────────────────────────┘
                        ▼
              ┌─────────────────────┐
              │  Camada Analytics   │
              │  (queries, indicadores,
              │   agregações, cache)│
              └──────────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │  FastAPI  │  │ Streamlit │  │  Notebooks│
    │  (REST)   │  │ (Dashboard)│  │ (Análise) │
    └───────────┘  └───────────┘  └───────────┘
```

**Princípios arquiteturais:**
- **Raw imutável**: dados brutos nunca modificados in-place
- **Qualidade first**: validações falham rápido e explicitamente
- **Separação de granularidades**: territorial (município) ≠ agrícola (município × produto × período)
- **CRS único**: EPSG:4674 no processamento, EPSG:4326 apenas na entrega ao mapa
- **Rastreabilidade total**: lineage completa em `docs/data-sources.md`

---

## Fontes de Dados

| Dataset | Fonte | Escopo | Licença |
|---------|-------|--------|---------|
| **PAM 2023** | IBGE SIDRA Tabela 5457 | Soja e Milho, MG, 2023 | Domínio público (IBGE) |
| **Malha Municipal 2023** | IBGE GeoFTP | 853 municípios MG | Domínio público (IBGE) |

**URLs oficiais:**
- PAM: https://sidra.ibge.gov.br/tabela/5457
- Malha: https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2023/UFs/MG/MG_Municipios_2023.zip

**Dados processados (não incluídos no repo):**
- `data/processed/ibge/malha_municipal/mg_municipios_2023.parquet` (42.9 MB)
- `data/processed/ibge/malha_municipal/mg_pam_2023_soja_milho.parquet` (44.5 MB)

> **Importante**: Os datasets brutos e processados **não fazem parte deste repositório** (ignorados via `.gitignore`). Use os scripts em `scripts/` para reproduzir o processamento a partir das fontes oficiais.

---

## Estrutura do Projeto

```
AgroData/
├── src/agrodata/              # Pacote principal
│   ├── api/                   # FastAPI routes + schemas
│   ├── analytics/             # Queries, indicadores, modelos
│   ├── config.py              # Configuração centralizada (paths, hash, CRS)
│   ├── geospatial/            # Ingest, validate, normalize, integrate, load
│   └── pipelines/ibge/        # Pipeline PAM completo
├── streamlit_app/             # Dashboard Streamlit
├── scripts/                   # Scripts utilitários (geração, análise, profiling)
├── tests/                     # 342 testes (unit + integração)
├── docs/
│   ├── data-sources.md        # Documentação completa de fontes e transformações
│   └── product-discovery.md   # Visão de produto e roadmap
├── data/                      # DADOS NÃO VERSIONADOS (ver .gitignore)
│   ├── raw/                   # Arquivos originais baixados
│   ├── processed/             # GeoParquets gerados
│   └── samples/               # Amostras para testes
├── notebooks/                 # Jupyter notebooks (futuro)
├── sql/                       # Migrações SQL (futuro)
├── pyproject.toml             # Configuração do projeto
├── README.md                  # Este arquivo
├── LICENSE                    # Licença MIT (código)
├── AGENTS.md                  # Instruções para agentes de desenvolvimento
└── .github/workflows/ci.yml   # CI/CD
```

---

## Instalação

### Pré-requisitos
- Python 3.13
- Git

### Com pip/venv
```bash
git clone https://github.com/<seu-usuario>/AgroData.git
cd AgroData

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"
```

### Com uv (recomendado - mais rápido)
```bash
git clone https://github.com/<seu-usuario>/AgroData.git
cd AgroData

uv venv
source .venv/bin/activate

uv pip install -e ".[dev]"
```

### Gerar datasets processados (necessário para rodar API/Streamlit)
```bash
# Baixa dados brutos do IBGE e gera GeoParquets em data/processed/
python scripts/gerar_parquets.py
```

---

## Executando os Testes

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=src/agrodata --cov-report=term-missing

# Apenas testes de analytics (cache, queries)
pytest tests/test_analytics.py -v

# Apenas testes geoespaciais
pytest tests/test_geospatial_*.py -v
```

**Resultado esperado:** 342 passed, 1 warning (deprecation pandas CRS override)

---

## Executando a API

```bash
# Terminal 1: Inicia API FastAPI em http://127.0.0.1:8000
uvicorn agrodata.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Endpoints disponíveis:**
| Endpoint | Descrição |
|----------|-----------|
| `GET /api/health` | Health check + metadados datasets |
| `GET /api/map/geojson` | FeatureCollection GeoJSON (EPSG:4326) |
| `GET /api/kpis` | KPIs agregados por filtro |
| `GET /api/ranking` | Top N municípios por indicador |
| `GET /api/municipality/{id}` | Detalhe completo de município |
| `GET /api/insights` | Insights automáticos |
| `GET /api/scatter` | Dados para gráfico Área × Produtividade |

**Parâmetros comuns:** `cultura` (Todos/Soja/Milho), `periodo` (2023), `indicador` (Produção/Área/Produtividade/Valor da produção)

---

## Executando o Streamlit

```bash
# Terminal 2: Inicia dashboard em http://localhost:8501
streamlit run streamlit_app/main.py
```

**Funcionalidades do dashboard:**
- Mapa coroplético interativo (Folium) com tooltip e clique
- KPIs: área total, produção total, produtividade ponderada, valor da produção
- Ranking Top 10 por indicador/cultura
- Scatter Área × Produtividade por município
- Detalhe de município ao clicar no mapa (percentil, ranking, valores)
- Insights automáticos (participação top 10, comparação com média)
- Filtros: cultura, período, indicador do mapa
- Data lineage na sidebar

---

## Dados Utilizados

### Camada Territorial (`mg_municipios_2023.parquet`)
- 853 municípios de Minas Gerais
- Geometria: limites municipais (EPSG:4674)
- Atributos: `municipio_id`, `municipio_nome`, `uf`, `area_km2`, `geometry`

### Camada Agrícola (`mg_pam_2023_soja_milho.parquet`)
- 1.137 observações (847 municípios × 2 produtos)
- Granularidade: `municipio_id` + `produto_codigo` + `periodo`
- Variáveis: área plantada (ha), produção (t), produtividade (kg/ha), valor (mil R$)
- Geometria herdada da malha (EPSG:4674)

### Integração
- **Estratégia**: PAM LEFT JOIN Malha por `municipio_id`
- **Resultado**: Observações agrícolas com geometria e atributos territoriais
- **6 municípios** da malha sem dados PAM (mantidos na malha territorial, não preenchidos com zero)

---

## Reprodutibilidade

O AgroData foi desenhado para ser reproduzível:

1. **Código versionado**: Toda lógica de ingestão, transformação e análise está em `src/`
2. **Scripts de geração**: `scripts/gerar_parquets.py` recria datasets processados a partir do raw
3. **Dados raw preservados**: Downloads originais mantidos em `data/raw/` (não modificados)
4. **Configuração centralizada**: `src/agrodata/config.py` define paths, CRS, colunas, indicadores
5. **Fingerprint de dataset**: Hash baseado em mtime+size dos Parquets invalida cache automaticamente
6. **Testes determinísticos**: 342 testes sem dependência de internet (fixtures locais)
7. **Dependências fixadas**: `pyproject.toml` com versões mínimas compatíveis

Para reproduzir do zero:
```bash
git clone <repo>
cd AgroData
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/gerar_parquets.py  # baixa do IBGE e processa
pytest  # valida tudo
uvicorn agrodata.api.main:app --reload
streamlit run streamlit_app/main.py
```

---

## Pesquisa / Desenvolvimento Futuro (Roadmap)

| MVP | Foco | Fontes Novas | Capacidades |
|-----|------|--------------|-------------|
| **MVP 1** | Base territorial + agrícola | IBGE PAM + Malha Municipal | Mapa produção, indicadores soja/milho |
| **MVP 2** | Clima + base | INMET (estações, histórico) | Risco climático, correlação clima-produção |
| **MVP 3** | Mercado + base | CONAB (estimativas safra) | Projeções, comparação PAM vs CONAB, alertas |
| **MVP 4** | Dados privados | Drones, sensores, APIs privadas | Integração público+privado, talhões, NDVI |
| **MVP 5** | Inteligência territorial | Modelos ML, alertas automáticos | Scoring risco, precificação, recomendações, ESG |

Veja `docs/product-discovery.md` para detalhes completos.

---

## Licença

**Código-fonte**: MIT License — veja arquivo [LICENSE](LICENSE).

> **Aviso importante**: A licença MIT aplica-se **apenas ao código deste projeto**. Os dados de terceiros utilizados (IBGE PAM, Malha Municipal IBGE) são de domínio público brasileiro, mas suas licenças originais devem ser respeitadas. Este projeto não redistribui datasets — apenas fornece código para processá-los a partir das fontes oficiais.

---

## Contribuindo

Contribuições são bem-vindas! Por favor:

1. Rode `ruff check .` e `pytest` antes de submeter PR
2. Mantenha validações explícitas (sem correções silenciosas tipo `buffer(0)`)
3. Documente fontes e transformações em `docs/data-sources.md`
4. Adicione testes para nova funcionalidade
5. Respeite a arquitetura: raw imutável, CRS único, separação de granularidades

---

## Referências

- [IBGE PAM - Pesquisa Agrícola Municipal](https://sidra.ibge.gov.br/tabela/5457)
- [IBGE Malhas Territoriais](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/)
- [GeoParquet Specification](https://geoparquet.org/)
- [SIRGAS 2000 (EPSG:4674)](https://epsg.io/4674)