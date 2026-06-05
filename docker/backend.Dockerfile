FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["sh", "-c", "if [ \"$SEED_DEMO_ON_START\" = \"true\" ]; then python -m backend.seed.seed_demo; fi; uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
