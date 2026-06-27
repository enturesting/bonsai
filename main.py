"""
main.py — Bonsai FastAPI entry point.
    dev:    uvicorn main:app --reload --port 8000
    deploy: uvicorn main:app --host 0.0.0.0 --port 8080 --timeout-keep-alive 75

NOTE: the web router + web/static are built by Terminal C (/web). Until they exist,
the include/mount are guarded so `uvicorn main:app` still serves /healthz for an
early smoke test.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import get_settings

logger = logging.getLogger("bonsai")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("Bonsai starting — grower=%s checker=%s db=%s mock_aut=%s",
                cfg.grower_model, cfg.checker_model, cfg.atlas_db, cfg.mock_aut)
    yield
    logger.info("Bonsai shutting down.")


app = FastAPI(
    title="Bonsai",
    description="Self-improving eval harness for cited-answer agents (AIEWF 2026)",
    version="0.1.0",
    lifespan=lifespan,
)

# Static + web router are created by Terminal C — guard so the app boots before then.
if os.path.isdir("web/static"):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

try:
    from web.routes import router as web_router
    app.include_router(web_router)
except Exception as e:  # web/routes.py not built yet
    logger.warning("web.routes not loaded yet (%s) — /healthz still available.", e)


@app.get("/healthz", tags=["ops"])
async def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "bonsai"})
