# Bonsai eval harness — DigitalOcean App Platform image (root Dockerfile so DO
# auto-detects it and builds with Docker, NOT the Python buildpack).
# Pins Python 3.12 — every pinned dep (voyageai 0.3.2, numpy 1.26.4, scipy 1.13.1)
# installs cleanly here; the buildpack's 3.13/3.14 has no wheels for them.
FROM python:3.12-slim

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

# --timeout-keep-alive 75 outlives DO's ~60s LB idle so long SSE streams aren't cut.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "75"]
