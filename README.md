# Personal Finance API

[![CI](https://github.com/dbduarte28/personal_finance_api/actions/workflows/ci.yml/badge.svg)](https://github.com/dbduarte28/personal_finance_api/actions/workflows/ci.yml)

A production-minded REST API for tracking personal income and expenses, built with FastAPI and PostgreSQL.

## Overview

Personal Finance API is a backend portfolio project focused on practical API design: authenticated
users can organize income and expense categories, record transactions, and retrieve an aggregated
financial summary. Every financial resource is scoped to its owner, monetary values use decimal
arithmetic, and summary calculations are performed in PostgreSQL.

Interactive API documentation is available at `/docs` after the application starts.

## Features

- Email and password registration with bcrypt password hashing
- OAuth2-compatible login with signed JWT access tokens
- User-owned income and expense categories with full CRUD operations
- User-owned transactions with decimal monetary values and full CRUD operations
- Transaction filtering by date range, category, and type, plus limit/offset pagination
- Financial summary with income, expenses, balance, and totals grouped by category
- Optional date filters for financial summaries
- Resource isolation that does not disclose another user's categories or transactions
- PostgreSQL-backed integration tests with transaction rollback
- Automated lint, formatting, test, and coverage checks in GitHub Actions

## Tech Stack

| Area | Technology |
| --- | --- |
| API | Python 3.12, FastAPI, Uvicorn |
| Validation | Pydantic, pydantic-settings |
| Database | PostgreSQL 16, SQLAlchemy 2 |
| Migrations | Alembic |
| Authentication | OAuth2 password flow, JWT, bcrypt |
| Testing | pytest, FastAPI TestClient, pytest-cov |
| Quality | Ruff |
| Infrastructure | Docker, Docker Compose, GitHub Actions |

## Project Structure

```text
.
|-- app/
|   |-- api/
|   |   |-- deps.py          # Shared API dependencies
|   |   `-- routes/          # HTTP endpoints grouped by resource
|   |-- core/                # Settings, database session, and security
|   |-- crud/                # Database queries and persistence operations
|   |-- models/              # SQLAlchemy models and enums
|   |-- schemas/             # Pydantic request and response models
|   `-- main.py              # FastAPI application and OpenAPI metadata
|-- alembic/                 # Database migration environment and revisions
|-- tests/                   # PostgreSQL-backed integration and unit tests
|-- .github/workflows/ci.yml # Continuous integration workflow
|-- docker-compose.yml
|-- Dockerfile
|-- pyproject.toml
`-- requirements*.txt
```

The codebase uses a deliberately small layered structure: routes handle HTTP concerns, CRUD modules
contain database access, schemas define the API contract, and models map the PostgreSQL tables.

## Docker Quickstart

Requirements: Docker and Docker Compose.

```bash
git clone https://github.com/dbduarte28/personal_finance_api.git
cd personal_finance_api
docker compose up --build -d
docker compose run --rm --volume .:/workspace --workdir /workspace api alembic upgrade head
```

The API is then available at `http://localhost:8000`, with Swagger UI at
`http://localhost:8000/docs`. The migration command is explicit because the API container does not
run migrations automatically.

Docker Compose provides development defaults and connects to PostgreSQL through the `db` hostname.
If you add a `.env` file for Docker, use `db` instead of `localhost` in both database URLs.

Stop the services without deleting PostgreSQL data:

```bash
docker compose down
```

## Local Installation

Requirements: Python 3.12 and a running PostgreSQL instance.

```bash
git clone https://github.com/dbduarte28/personal_finance_api.git
cd personal_finance_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

Create the application and test databases, adjusting the PostgreSQL user when necessary:

```bash
psql -U postgres -c "CREATE DATABASE personal_finance;"
psql -U postgres -c "CREATE DATABASE personal_finance_test;"
alembic upgrade head
uvicorn app.main:app --reload
```

## Environment Variables

Copy `.env.example` to `.env` and adjust it for your environment. The `.env` file is ignored by Git.

| Variable | Purpose | Example |
| --- | --- | --- |
| `APP_NAME` | Application name used by the settings layer | `Personal Finance API` |
| `ENVIRONMENT` | Runtime environment label | `development` |
| `DATABASE_URL` | SQLAlchemy URL for the application database | `postgresql+psycopg://postgres:postgres@localhost:5432/personal_finance` |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL database used by tests | `postgresql+psycopg://postgres:postgres@localhost:5432/personal_finance_test` |
| `SECRET_KEY` | Secret used to sign JWTs; replace outside local development | Generate a long random value |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes | `60` |

Never reuse the placeholder secret from `.env.example` in a deployed environment.

## Database Migrations

Apply every migration:

```bash
alembic upgrade head
```

Check whether model metadata would require a new migration:

```bash
alembic check
```

Create a migration after an intentional model change:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

## Tests and Coverage

The test suite requires the PostgreSQL database configured by `TEST_DATABASE_URL`. Tests create the
schema for the session and isolate individual cases with transaction rollback.

```bash
pytest
```

Coverage is configured in `pyproject.toml`; the command prints missing lines and fails below 80%.
The current suite contains 69 tests and reports **97.30% total coverage**.

Run the same quality checks used by CI:

```bash
ruff check .
ruff format --check .
pytest
```

## Authentication

Register with an email and password at `POST /api/v1/auth/register`. Then submit form-encoded
credentials to `POST /api/v1/auth/login`, using the email in the OAuth2 `username` field. The response
contains a bearer access token.

Send the token to protected endpoints:

```http
Authorization: Bearer <access_token>
```

Passwords are stored only as bcrypt hashes and are never included in API responses. The current
authentication scope uses access tokens only; refresh tokens and password recovery are not included.

## Main Endpoints

| Method | Endpoint | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Check API availability |
| `POST` | `/api/v1/auth/register` | No | Register a user |
| `POST` | `/api/v1/auth/login` | No | Obtain a JWT access token |
| `GET` | `/api/v1/users/me` | Yes | Read the authenticated user |
| `POST` | `/api/v1/categories` | Yes | Create a category |
| `GET` | `/api/v1/categories` | Yes | List the user's categories |
| `GET` | `/api/v1/categories/{category_id}` | Yes | Read a category |
| `PATCH` | `/api/v1/categories/{category_id}` | Yes | Update a category |
| `DELETE` | `/api/v1/categories/{category_id}` | Yes | Delete a category |
| `POST` | `/api/v1/transactions` | Yes | Create a transaction |
| `GET` | `/api/v1/transactions` | Yes | List and filter transactions |
| `GET` | `/api/v1/transactions/{transaction_id}` | Yes | Read a transaction |
| `PATCH` | `/api/v1/transactions/{transaction_id}` | Yes | Update a transaction |
| `DELETE` | `/api/v1/transactions/{transaction_id}` | Yes | Delete a transaction |
| `GET` | `/api/v1/summary` | Yes | Get aggregated financial totals |

See `/docs` for request schemas, response schemas, query parameters, and interactive examples.

## Continuous Integration

The GitHub Actions workflow runs on every push and pull request targeting `main`. It starts a
PostgreSQL 16 service, installs application and development dependencies, checks Ruff lint and
formatting, and runs the complete test suite with the 80% coverage threshold.

## Roadmap

The first version intentionally keeps its scope focused. Potential future work includes:

- Refresh tokens, password recovery, and role-based permissions
- Multiple bank accounts, budgets, goals, recurring transactions, and statement imports
- Multiple currencies and a frontend client
- Operational features such as rate limiting, Redis caching, and soft deletion
- Async SQLAlchemy only if future workload requirements justify the additional complexity

These items are not implemented in the current API.

## License

This project is available under the [MIT License](LICENSE).
