# Deployment Guide

## Backend on Railway

### 1. Create a Railway Project

- Create a new project at [railway.app](https://railway.app).
- Add a **PostgreSQL** service (Railway provisions and manages it).
- Add a **Redis** service.

### 2. Deploy the Backend

- Connect your repository.
- Set the Dockerfile path to `docker/backend.Dockerfile`.
- Railway builds and deploys automatically on push.

### 3. Configure Environment Variables

Set these in the Railway service settings:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Provided by Railway's PostgreSQL service (use the `postgresql+psycopg://` format) |
| `REDIS_URL` | Provided by Railway's Redis service |
| `JWT_SECRET` | A strong, randomly generated secret (e.g., `openssl rand -hex 32`) |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` |
| `CORS_ORIGINS` | Your Vercel frontend URL (e.g., `https://plum.vercel.app`) |

### 4. Database Setup

Railway provisions PostgreSQL automatically. Tables are created on first backend startup via SQLAlchemy's `create_all`.

To seed demo data (demo environments only):

```bash
railway run python -m backend.seed.seed_demo
```

### 5. Verify

Check the health endpoint:

```bash
curl https://your-backend.up.railway.app/health
# {"status": "ok"}
```

---

## Frontend on Vercel

### 1. Import the Repository

- Import your repository in the [Vercel dashboard](https://vercel.com).
- Set the **Root Directory** to `frontend`.

### 2. Configure Environment Variables

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Your Railway backend URL (e.g., `https://your-backend.up.railway.app`) |

### 3. Deploy

Vercel auto-detects Next.js and uses the default build command (`next build`). Deploy on push.

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
