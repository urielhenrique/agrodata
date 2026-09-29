# Product Discovery — AgroData

## Visão de Produto

O AgroData não é apenas uma solução de scraping ou ETL de dados públicos. O objetivo é **transformar dados públicos e privados georreferenciados em inteligência territorial** para apoiar decisões de negócio no agronegócio e setores correlatos.

A plataforma deve permitir:
- Ingestão, normalização e qualidade de dados geoespaciais heterogêneos
- Integração espacial e temporal de múltiplas fontes
- Geração de indicadores, mapas, dashboards e alertas
- Rastreabilidade total: todo insight deve ser rastreável às fontes e transformações que o produziram

---

## Personas Iniciais

### 1. Produtor / Cooperativa
- Necessita: visibilidade da produção própria e de vizinhos, benchmarks regionais, indicadores de risco climático e de mercado
- Dados relevantes: PAM, CONAB, INMET, dados de campo próprios
- Decisões: planejamento de safra, negociação de contratos, gestão de risco

### 2. Empresa de Geotecnologia com Dados Proprietários (ex: Aero Engenharia)
- Necessita: integrar ortomosaicos, nuvens de pontos, shapefiles e GeoJSON de drones com dados públicos
- Dados relevantes: voos de drone, sensoriamento remoto próprio, APIs privadas
- Decisões: enriquecer produtos próprios, oferecer análises combinadas público+privado

### 3. Tomadores de Decisão Territorial
- Bancos e seguradoras: scoring de risco agrícola, garantias, precificação de crédito rural
- Empresas de insumos: dimensionamento de mercado, logística, posicionamento de produtos
- Mineração: licenciamento, áreas de influência, compensação ambiental
- Empresas ambientais: monitoramento, compliance, relatórios ESG
- Setor público: planejamento territorial, políticas agrícolas, zoneamento

---

## Conceito de Dados

### Fontes Públicas
| Fonte | Tipo | Exemplos de Dados |
|-------|------|-------------------|
| IBGE | Censo, PAM, Malhas | Produção agrícola, limites municipais, demografia |
| INMET | Meteorologia | Temperatura, precipitação, umidade, estações |
| CONAB | Safras | Estimativas de área, produção, produtividade |
| ANA | Recursos hídricos | Bacias, outorgas, qualidade da água |
| MapBiomas | Cobertura do solo | Uso da terra, desmatamento, transições |
| INPE | Sensoriamento remoto | Queimadas, DETER, PRODES, CBERS |

### Fontes Privadas
- Drones: ortomosaicos, DSM/DTM, nuvens de pontos, índices vegetativos (NDVI, EVI, etc.)
- Sensores IoT: umidade do solo, temperatura, pluviômetros
- Levantamentos de campo: amostragem de solo, pragas, doenças, inventário florestal
- APIs privadas: marketplaces de dados, provedores de satélite comercial, ERPs agrícolas
- Formatos: GeoJSON, Shapefile, GeoTIFF, COG, Parquet geoespacial, bancos PostGIS

### Dados de Campo / Operacionais
- Cadastro de talhões/propriedades
- Histórico de operações (plantio, colheita, aplicações)
- Máquinas e telemetria
- Notas fiscais, contratos, recibos

---

## Arquitetura Conceitual

```
FONTE PÚBLICA          FONTE PRIVADA
    │                      │
    ▼                      ▼
┌─────────────────────────────────────┐
│         INGESTÃO                    │
│  (API, FTP, upload, streaming)      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│           RAW                       │
│  Preservação integral da fonte      │
│  Metadados: origem, coleta, versão  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│        NORMALIZAÇÃO                 │
│  Schemas padronizados               │
│  CRS unificado                      │
│  Chaves de integração (municipio_id,│
│  talhao_id, data, geometria)        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│          QUALIDADE                  │
│  Validações de schema               │
│  Completitude, consistência         │
│  Geometria válida (sem buffer(0))   │
│  Duplicidade, outliers              │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       DADOS PROCESSADOS             │
│  GeoParquet particionado            │
│  Catálogo de datasets               │
│  Versionamento                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│   INTEGRAÇÃO ESPACIAL/TEMPORAL      │
│  Joins espaciais (intersects,       │
│  contains, within)                  │
│  Joins temporais (asof, window)     │
│  Agregação por grade/H3/município   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│         INDICADORES                 │
│  Produtividade, risco, tendência    │
│  Benchmarks regionais               │
│  Alertas (climáticos, mercado)      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│      MAPAS / DASHBOARDS / ALERTAS   │
│  Visualização interativa            │
│  API para consumo externo           │
│  Exportação de relatórios           │
└─────────────────────────────────────┘
```

---

## Metadados Obrigatórios para Dados Privados

Todo dataset privado ingerido deve carregar metadados mínimos:

| Metadado | Descrição |
|----------|-----------|
| `source_id` | Identificador único da fonte |
| `source_type` | Tipo: drone, sensor, API, levantamento, ERP |
| `collection_date` | Data/hora da coleta/voo/medição |
| `reference_period` | Período de referência dos dados (safra, mês, dia) |
| `geometry_type` | Point, Polygon, Raster, LineString |
| `crs` | Sistema de referência espacial (EPSG) |
| `resolution` | Resolução espacial (m/pixel para raster) |
| `processing_level` | Raw, ortorretificado, calibrado, derivado |
| `owner` | Proprietário dos dados |
| `license` | Licença/restrição de uso |
| `lineage` | Transformações aplicadas desde a origem |

---

## Primeiro MVP (MVP 1)

**Objetivo:** Demonstrar a arquitetura completa com fontes públicas consolidadas.

**Escopo:**
- IBGE PAM 2023 (soja e milho) + Malha Municipal MG 2023
- Mapa de produção agrícola por município
- Indicadores: área plantada, produção, produtividade, valor da produção
- Filtros por produto, município, comparação com média estadual

**Entregáveis:**
- `mg_municipios_2023.parquet` (853 municípios, CRS EPSG:4674)
- `mg_pam_2023_soja_milho.parquet` (1.137 observações, 847 municípios)
- Documentação de fontes e transformações
- 308 testes automatizados passando

---

## Evolução Planejada

| MVP | Foco | Fontes Adicionadas | Novas Capacidades |
|-----|------|-------------------|-------------------|
| **MVP 1** | Base territorial + agrícola | IBGE PAM + Malha Municipal | Mapa produção, indicadores soja/milho |
| **MVP 2** | Clima + base | + INMET (estações, histórico) | Risco climático, correlação clima-produção |
| **MVP 3** | Mercado + base | + CONAB (estimativas safra) | Projeções, comparação PAM vs CONAB, alertas de desvio |
| **MVP 4** | Dados privados | + Drones, sensores, APIs privadas | Integração público+privado, talhões, NDVI, solo |
| **MVP 5** | Inteligência territorial | Modelos, ML, alertas automáticos | Scoring de risco, precificação, recomendações, ESG |

---

## Princípios Arquiteturais

1. **Rastreabilidade total**: Todo insight deve ser rastreável às fontes e transformações que o produziram (lineage completa).

2. **RAW imutável**: Dados brutos nunca são modificados in-place. Transformações geram novas versões.

3. **Qualidade como cidadão de primeira classe**: Validações falham rápido e explicitamente. Nenhuma correção automática silenciosa (ex: `buffer(0)` proibido).

4. **Separação de granularidades**: Camada territorial (município) ≠ camada agrícola (município × produto × período) ≠ camada de talhão.

5. **Dados privados com metadados obrigatórios**: Sem metadados de origem, não entra no catálogo.

6. **CRS único no processamento**: EPSG:4674 (SIRGAS 2000) como padrão para Brasil. Reprojeção só na borda de visualização.

6. **GeoParquet como formato de intercâmbio**: Preserva geometry, CRS, tipos. Particionamento por estado/ano.

7. **Testes determinísticos**: Sem dependência de internet. Fixtures locais para validação de pipelines.

8. **Documentação viva**: `docs/data-sources.md` e `docs/product-discovery.md` atualizados a cada MVP.

---

## Próximos Passos Imediatos

1. Validar MVP 1 com stakeholders (produtor, geotecnologia, banco)
2. Definir schema de metadados para catálogo de datasets
3. Implementar ingestão INMET (estações + histórico) para MVP 2
4. Definir modelo de dados para talhões/propriedades (MVP 4)
5. Avaliar stack de visualização (Leaflet/MapLibre + backend tile server ou COG)