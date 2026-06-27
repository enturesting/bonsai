# Bonsai eval harness — DigitalOcean App Platform image
# Serves `main:app` (FastAPI). /healthz is the DO health check (main.py).
FROM python:3.12-slim

# Faster, quieter Python in a container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so the layer caches across code-only changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# App source
COPY . .

EXPOSE 8080

# Matches CONTRACTS.md §/deploy. --timeout-keep-alive 75 outlives DO's 60s LB idle
# so long-lived SSE streams (/stream/improve) aren't cut mid-flight.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "75"]
