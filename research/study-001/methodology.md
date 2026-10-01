# Methodology

## 1. Study Design

This is an exploratory quantitative study based on the integration of
official agricultural, meteorological, and territorial datasets.

The initial geographic scope is Minas Gerais, Brazil.

The primary analytical unit is municipality × year.

## 2. Data Sources

### 2.1 Agricultural

IBGE Produção Agrícola Municipal (PAM).

### 2.2 Meteorological

INMET official meteorological data.

The AgroData infrastructure considers:

- BDMEP;
- WIS2;
- apitempo.

### 2.3 Geographic

IBGE municipal boundaries.

## 3. Data Processing

The processing pipeline consists of:

1. ingestion;
2. parsing;
3. normalization;
4. quality validation;
5. spatial association;
6. temporal aggregation;
7. integration;
8. analytical dataset generation.

## 4. Spatial Processing

Meteorological stations are represented as points.

Municipal boundaries are represented as polygons or multipolygons.

The initial association rule is:

    municipality contains station point

Municipality assignment based solely on textual station names will not be used.

## 5. Temporal Processing

Meteorological observations will be transformed into annual indicators.

Candidate indicators include:

- annual precipitation;
- annual mean temperature;
- annual maximum temperature;
- annual minimum temperature.

Additional indicators may be defined according to data availability and
research requirements.

## 6. Data Quality

Quality validation will consider:

- missing values;
- invalid physical ranges;
- duplicated observations;
- temporal consistency;
- station status;
- completeness;
- source provenance.

Invalid observations will not be silently removed without documenting the
transformation.

## 7. Dataset Integration

The principal join key between the agricultural and territorial datasets will
be the IBGE municipality identifier.

Climate data will first be associated spatially with municipalities and then
integrated with agricultural statistics.

## 8. Exploratory Analysis

The first analytical stage will include:

- descriptive statistics;
- distributions;
- temporal variation;
- spatial distributions;
- correlation analysis.

## 9. Statistical Analysis

Candidate statistical methods include:

- Pearson correlation;
- Spearman correlation;
- simple linear regression.

The final statistical methods will be selected after evaluating the
distribution and structure of the resulting dataset.

## 10. Reproducibility

All transformations should be implemented in version-controlled code.

The study should be executable using documented software dependencies and
parameters.

Each derived dataset should have documented provenance.

## 11. Causal Interpretation

The study will not interpret statistical association as evidence of causation.

Potential confounding factors will be documented as limitations.

## 12. Validation

Before statistical analysis, the following will be checked:

- number of municipalities;
- number of agricultural observations;
- number of meteorological stations;
- number of station-to-municipality associations;
- missing climate observations;
- temporal coverage;
- duplicate records;
- invalid observations.

## 13. Reproducibility Checklist

- [ ] Data sources documented
- [ ] Data extraction reproducible
- [ ] Transformations version controlled
- [ ] Quality rules documented
- [ ] Spatial join reproducible
- [ ] Temporal aggregation documented
- [ ] Analytical dataset reproducible
- [ ] Statistical parameters documented
- [ ] Results reproducible
