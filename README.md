# Plum OPD Claim Adjudication Tool

AI-assisted OPD claim document understanding with deterministic, auditable policy adjudication.

## Architecture Overview

A claim flows through five stages:

1. **Upload** — The member uploads prescription and medical bill documents (with an optional diagnostic report) through the Next.js frontend.
2. **OCR** — The backend runs Docling (with an EasyOCR fallback) to extract raw text and a per-document confidence score.
3. **AI Extraction** — GPT-4o converts the raw OCR text into structured fields using Pydantic models. The LLM output is constrained to a strict schema; it never makes approval decisions.
4. **Rule Engine** — A deterministic engine evaluates eligibility, document validation, coverage, limits, medical necessity, and fraud checks against JSON policy configuration. No LLM is involved in the decision.
5. **Decision** — The engine produces one of four outcomes: `APPROVED`, `REJECTED`, `PARTIAL`, or `MANUAL_REVIEW`. Every triggered rule is logged for audit.

> **Key design principle:** The LLM extracts information only. A deterministic rule engine makes all decisions.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, TailwindCSS, shadcn/ui components |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| AI Extraction | OpenAI GPT-4o with Pydantic structured outputs |
| OCR | Docling with EasyOCR fallback |
| Cache | Redis 7 |
| Deployment | Docker Compose (local), Railway (backend), Vercel (frontend) |
| Testing | Pytest |

## Quick Start

```bash
docker compose up --build
```

Seed demo data:

```bash
docker compose exec backend python -m backend.seed.seed_demo
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |

### Demo Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@plum.demo` | `admin123` |
| Member | `member@plum.demo` | `member123` |

## Project Structure

```text
plum/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers (auth, claims, admin)
│   │   ├── core/           # Settings, security, JWT
│   │   ├── db/             # Database session and engine
│   │   ├── models/         # SQLAlchemy ORM models (8 tables)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (OCR, extraction, rule engine, fraud)
│   │   └── workers/        # Background task workers
│   ├── config/
│   │   └── opd_policy.json # Policy limits, exclusions, network rules
│   ├── seed/               # Demo data seeding scripts
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js App Router pages
│   ├── components/         # React UI components
│   └── lib/                # API client utilities
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── docs/                   # Project documentation
├── tests/                  # Pytest test suite
└── docker-compose.yml
```

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create a user account |
| `POST` | `/auth/login` | — | Get a JWT bearer token |
| `POST` | `/claims` | User | Submit a claim with document uploads |
| `GET` | `/claims` | User | List the authenticated user's claims |
| `GET` | `/claims/{id}` | User | Get claim detail |
| `GET` | `/claims/{id}/processing` | User | Get processing stage status |
| `GET` | `/admin/dashboard` | Admin | Aggregate metrics and decision distribution |
| `GET` | `/admin/claims` | Admin | List all claims |
| `GET` | `/admin/manual-reviews` | Admin | Manual review queue |
| `POST` | `/admin/manual-reviews/{id}/override` | Admin | Override a flagged claim decision |
| `GET` | `/health` | — | Health check |

See [docs/api.md](docs/api.md) for full request/response examples.

## Documentation

- [Architecture](docs/architecture.md) — System design, processing pipeline, database schema
- [API Documentation](docs/api.md) — Endpoint reference with example payloads
- [Adjudication Rules](docs/adjudication-rules.md) — Complete rule engine specification
- [Setup Guide](docs/setup.md) — Docker and local development setup
- [Deployment Guide](docs/deployment.md) — Railway and Vercel deployment
- [Sample Screenshots](docs/sample-screenshots.md)

## Testing

```bash
python -m pytest tests/ -v
```

The test suite covers the rule engine, fraud detection module, and confidence engine with deterministic unit tests that do not require a database or API keys.

## Deployment

- **Backend:** Railway with PostgreSQL and Redis add-ons. Uses `docker/backend.Dockerfile`.
- **Frontend:** Vercel with `NEXT_PUBLIC_API_BASE_URL` pointing to the Railway backend.

See [docs/deployment.md](docs/deployment.md) for full instructions.
