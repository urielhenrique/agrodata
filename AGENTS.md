# AgroData — Agent Instructions

## 1. Project Goal

AgroData is a learning and portfolio project focused on:

- Data Engineering
- Web/API data collection
- ETL/ELT
- Geospatial data
- Agribusiness data
- Spatial analysis
- Remote sensing
- Machine Learning
- Geospatial AI

The project should evolve incrementally from a simple data pipeline into a professional geospatial data platform.

---

## 2. Current Technology Stack

Primary language:

- Python 3.13

Current tools:

- VS Code
- Git
- pytest
- Ruff
- Docker

Planned technologies:

- PostgreSQL
- PostGIS
- Pandas
- Polars
- GeoPandas
- Shapely
- PyProj
- Rasterio
- QGIS
- Airflow or Prefect
- Machine Learning
- Remote Sensing

Do not add planned technologies until they are required by the current development stage.

---

## 3. Development Principles

Follow these principles:

1. Prefer simple solutions over unnecessary complexity.
2. Do not implement features that were not requested.
3. Do not introduce dependencies without explaining why they are necessary.
4. Prefer official APIs over web scraping when an official API is available.
5. Respect website terms of use, robots.txt, licenses, rate limits and applicable laws.
6. Never bypass authentication, access controls or anti-bot protections.
7. Never store credentials, API keys or secrets in source code.
8. Use environment variables for secrets and configuration.
9. Validate external data before storing or processing it.
10. Make data pipelines reproducible whenever possible.

---

## 4. Code Quality

All Python code must:

- Follow clear naming conventions.
- Prefer type hints.
- Keep functions small and focused.
- Avoid unnecessary global state.
- Handle expected errors explicitly.
- Include useful logging where appropriate.

Run Ruff before considering a task complete:

    python -m ruff check .

---

## 5. Testing

New functionality should include tests whenever practical.

Run:

    python -m pytest

Tests should cover:

- normal cases
- invalid input
- expected failures
- important edge cases

Do not remove or weaken existing tests simply to make a test suite pass.

---

## 6. Project Structure

Current structure:

    AgroData/
    ├── src/
    │   └── agrodata/
    ├── tests/
    ├── data/
    │   ├── raw/
    │   ├── processed/
    │   └── samples/
    ├── notebooks/
    ├── sql/
    ├── docs/
    ├── AGENTS.md
    ├── README.md
    ├── pyproject.toml
    └── .gitignore

Keep responsibilities separated.

---

## 7. Data Rules

Raw external data must not be modified in place.

Prefer:

    data/raw/
        ↓
    transformation
        ↓
    data/processed/

Do not commit large datasets to Git unless explicitly requested.

Do not commit private, confidential or restricted data.

Document the source of external datasets.

Record relevant metadata when practical:

- source
- collection date
- geographic coverage
- format
- coordinate reference system
- license
- transformation steps

---

## 8. Geospatial Rules

When geospatial functionality is introduced:

- Always identify the coordinate reference system (CRS).
- Never assume latitude/longitude without validation.
- Document EPSG codes when applicable.
- Distinguish vector and raster data.
- Validate geometries when necessary.
- Be careful with coordinate transformations.
- Avoid calculating distances or areas using inappropriate geographic coordinate systems.

---

## 9. Database Rules

When PostgreSQL/PostGIS is introduced:

- Use migrations or versioned SQL when appropriate.
- Do not hardcode credentials.
- Use parameterized queries.
- Document important indexes.
- Consider spatial indexes for spatial queries.
- Separate transactional data from analytical processing when necessary.

---

## 10. Agent Behavior

Before modifying the project:

1. Inspect the existing structure.
2. Read relevant documentation.
3. Understand existing implementation.
4. Explain the proposed change.
5. Make the smallest reasonable change.
6. Run relevant tests.
7. Run Ruff.
8. Report what changed and any remaining issues.

Do not rewrite working code unnecessarily.

Do not modify architecture without explicit justification.

---

## 11. Learning Objective

This is also a learning project.

When implementing non-trivial functionality:

- Explain important technical decisions.
- Identify relevant concepts to learn.
- Prefer understandable code over clever code.
- Do not hide important logic behind unnecessary abstractions.

The developer should be able to understand and explain the implementation.
