# Corrup.ORG

> **API for integrating and analysing public-organization financial data to detect missing funds and other irregularities.**

## Overview

Corrup.ORG exposes a RESTful API built with [FastAPI](https://fastapi.tiangolo.com/) that lets you:

- Manage **public organizations** (federal, state, municipal, NGO, …)
- Track **fund allocations** and their execution status for each organization
- Import fund data directly from the **Portal da Transparência** (Brazilian federal transparency portal)
- Run **analysis endpoints** to detect missing funds, cross-reference irregularities across organizations, and get expenditure breakdowns by category

---

## Quick start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env – at minimum set TRANSPARENCIA_API_KEY if you want live data
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

The interactive API docs are available at **http://localhost:8000/docs**.

---

## API Endpoints

### Organizations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/organizations/` | List organizations (filter by category, state, name) |
| `POST` | `/organizations/` | Create an organization |
| `GET` | `/organizations/{id}` | Get a single organization |
| `PATCH` | `/organizations/{id}` | Partially update an organization |
| `DELETE` | `/organizations/{id}` | Delete an organization (cascades to funds) |

### Funds

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/funds/` | List funds (filter by org, category, status, year) |
| `POST` | `/funds/` | Create a fund record |
| `GET` | `/funds/{id}` | Get a single fund |
| `PATCH` | `/funds/{id}` | Partially update a fund |
| `DELETE` | `/funds/{id}` | Delete a fund |
| `POST` | `/funds/import/external` | Import fund records from Portal da Transparência |

### Analysis

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/analysis/missing-funds` | Funds where executed < allocated (potential missing money) |
| `GET` | `/analysis/categories` | Financial breakdown by expenditure category |
| `GET` | `/analysis/cross-reference` | Organizations sharing categories with missing funds |
| `GET` | `/analysis/summary` | Overall financial health + per-organization risk levels |

---

## Development

### Run tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Project structure

```
app/
├── main.py              # FastAPI application & lifespan hooks
├── config.py            # Settings (pydantic-settings / .env)
├── database/
│   └── db.py            # SQLAlchemy engine, session, Base
├── models/
│   ├── organization.py  # ORM model + Pydantic schemas
│   ├── fund.py          # ORM model + Pydantic schemas
│   └── analysis.py      # Pydantic response schemas for analysis
├── routers/
│   ├── organizations.py # CRUD endpoints
│   ├── funds.py         # CRUD + external import endpoints
│   └── analysis.py      # Analysis endpoints
└── services/
    ├── analyzer.py      # Business logic: missing-fund & cross-ref computations
    └── data_fetcher.py  # HTTP client for Portal da Transparência
tests/
├── conftest.py          # Shared fixtures (in-memory SQLite, TestClient)
├── test_organizations.py
├── test_funds.py
└── test_analysis.py
```

---

## External data source

The `/funds/import/external` endpoint fetches **convenios** (agreement records) from the [Portal da Transparência API](https://portaldatransparencia.gov.br/api-de-dados/swagger-ui.html).  
Set `TRANSPARENCIA_API_KEY` in your `.env` to enable live imports.  
Without a key the endpoint returns an empty list and logs a warning — useful for local development.

---

## License

MIT © EduardoEurico
