# Deployment Guide

## Backend on Render

This repository includes a Render Blueprint at `render.yaml`.

### 1. Create the Render Blueprint

- Open [Render Blueprints](https://dashboard.render.com/blueprints).
- Select this GitHub repository: `sarthak06shukla/Plum_Assignment`.
- Render will create:
  - `plum-assignment-backend` web service
  - `plum-assignment-db` PostgreSQL database

The backend uses `docker/backend.Dockerfile` and starts with Render's `$PORT`.

### 2. Configure Environment Variables

The blueprint sets the required deployment variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | From Render PostgreSQL |
| `JWT_SECRET` | Auto-generated |
| `CORS_ORIGINS` | Vercel frontend URL |
| `EASYOCR_DOWNLOAD_ENABLED` | `true` |
| `SEED_DEMO_ON_START` | `true` |
| `OPENAI_MODEL` | `gpt-4o` |

Optional:

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | Your OpenAI API key, if you want OpenAI extraction instead of the local fallback |

### 3. Database Setup

Tables are created on first backend startup via SQLAlchemy's `create_all`.
When `SEED_DEMO_ON_START=true`, demo users and sample claims are seeded idempotently.

Demo credentials:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@plum.demo` | `admin123` |
| Member | `member@plum.demo` | `member123` |

### 4. Verify

Check the health endpoint:

```bash
curl https://your-render-service.onrender.com/health
# {"status": "ok"}
```

---

## Frontend on Vercel

Vercel is the recommended frontend host for this Next.js app.

### 1. Import the Repository

- Open [Vercel](https://vercel.com/new).
- Import `sarthak06shukla/Plum_Assignment`.
- Set **Root Directory** to:

```text
frontend
```

Vercel will use `frontend/vercel.json` and auto-detect Next.js.

### 2. Configure Frontend API URL

In Vercel project settings, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Render backend URL |

### 3. Deploy

Deploy the Vercel project. Future pushes to `main` deploy automatically.

### 4. Update Render CORS

After Vercel gives you the final frontend URL, set the Render backend environment variable:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | Your Vercel URL, e.g. `https://plum-assignment.vercel.app` |

Redeploy the Render backend after updating `CORS_ORIGINS`.

Frontend URL example:

```text
https://plum-assignment.vercel.app
```

---

## Production Considerations

### File Storage

Replace local file storage with an object storage service:

- **AWS S3**, **Google Cloud Storage**, or **Cloudflare R2**.
- Update `DocumentUploadService` to write to and read from the object store.
- Configure signed URLs for secure document access.

### Database

- Use Railway's managed PostgreSQL or a dedicated provider (e.g., Neon, Supabase, RDS).
- Enable automated backups and point-in-time recovery.
- Monitor connection pool usage under load.

### Security

- **JWT Secret:** Rotate `JWT_SECRET` periodically. Use a cryptographically strong value (≥ 32 bytes).
- **CORS:** Restrict `CORS_ORIGINS` to only the production frontend domain. Do not use `*`.
- **API Key:** Store `OPENAI_API_KEY` as a secret in your deployment platform. Do not commit it to the repository.

### Monitoring

- Enable audit log monitoring. All admin overrides are logged to the `audit_logs` table.
- Set up alerts for claims routed to `MANUAL_REVIEW` to ensure timely reviewer action.
- Monitor OCR and extraction confidence trends to detect document quality degradation.

### Scaling

- The FastAPI backend is stateless. Scale horizontally by adding replicas.
- PostgreSQL handles concurrent reads well; use connection pooling (e.g., PgBouncer) for high write loads.
- Redis is used for caching; consider Redis Cluster for high availability.
