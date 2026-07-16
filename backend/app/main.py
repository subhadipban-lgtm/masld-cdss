"""MASLD DrugScope FastAPI application entry point.

Creates the application, registers middleware (CORS, request logging),
includes the API router, and runs startup validation.
"""

import time
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_cors_middleware_kwargs

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ────────────────────────────────────────────────────────
    logger.info(
        f"MASLD DrugScope API starting — "
        f"pipeline_version={settings.pipeline_version}, "
        f"model_version={settings.model_version}"
    )

    # Validate reference data directory.
    ref_dir = settings.reference_data_path
    if ref_dir.exists():
        logger.info(f"Reference data directory found: {ref_dir}")
    else:
        logger.warning(
            f"Reference data directory not found: {ref_dir}. "
            f"Pipeline will fail at inference time."
        )

    # Log key configuration values.
    logger.info(
        f"Config — REDIS_URL={settings.redis_url}, "
        f"MAX_UPLOAD_SIZE_MB={settings.max_upload_size_mb}, "
        f"GENCODE_VERSION={settings.gencode_version}, "
        f"SALMON_INDEX_DIR={settings.salmon_index_dir}"
    )

    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("MASLD DrugScope API shutting down.")


app = FastAPI(
    title="MASLD DrugScope API",
    description="GNN-Powered Therapeutic Hypothesis Engine for MASLD",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────

app.add_middleware(CORSMiddleware, **get_cors_middleware_kwargs())

# ── Request Logging Middleware ─────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request's method, path, response status, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} "
        f"({duration_ms:.1f}ms)"
    )
    return response


# ── Router ─────────────────────────────────────────────────────────────

app.include_router(router)