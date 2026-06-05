# Setup Guide

## Docker Setup (Recommended)

Docker Compose starts PostgreSQL, Redis, the FastAPI backend, and the Next.js frontend in one command.

### Prerequisites

- Docker and Docker Compose
- (Optional) An OpenAI API key for live AI extraction

### Steps

1. **Create a `.env` file** in the project root (optional, for live extraction):

```bash
OPENAI_API_KEY=sk-...
```

The Docker Compose file provides defaults for all other variables (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `OPENAI_MODEL`).

2. **Start all services:**

```bash
docker compose up --build
```

3. **Seed demo data:**

```bash
docker compose exec backend python -m backend.seed.seed_demo
```

4. **Open the application:**

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |

5. **Demo credentials:**

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@plum.demo` | `admin123` |
| Member | `member@plum.demo` | `member123` |

---

## Local Setup Without Docker

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- Redis 7

### 1. PostgreSQL

Create a database and user:

```sql
CREATE USER plum WITH PASSWORD 'plum';
CREATE DATABASE plum OWNER plum;
```

### 2. Environment Variables

Create a `.env` file in the project root:

```bash
DATABASE_URL=postgresql+psycopg://plum:plum@localhost:5432/plum
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=replace-with-a-strong-secret
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
CORS_ORIGINS=http://localhost:3000
```

### 3. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

The backend runs at http://localhost:8000. Tables are created automatically on startup.

### 4. Seed Demo Data

```bash
python -m backend.seed.seed_demo
```

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at http://localhost:3000.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (`postgresql+psycopg://user:pass@host:5432/db`) |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `JWT_SECRET` | Yes | — | Secret key for JWT token signing. Use a strong random value in production |
| `OPENAI_API_KEY` | No | — | OpenAI API key. Required for live AI extraction. Without it, extraction returns mock data |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model name |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of allowed frontend origins |
| `NEXT_PUBLIC_API_BASE_URL` | Yes (frontend) | — | Backend API URL as seen by the browser |

---

## Running Tests

Tests run without a database or API keys:

```bash
python -m pytest tests/ -v
```

The test suite covers:

- **Rule engine:** Deterministic adjudication logic for all rule categories
- **Fraud detection:** All five fraud check scenarios
- **Confidence engine:** Score calculation with various input combinations
