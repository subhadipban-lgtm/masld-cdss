"""FastAPI router for the MASLD DrugScope API.

Endpoints
---------
POST /api/v1/upload   — Accept a FASTQ file + clinical params; enqueue pipeline
GET  /api/v1/status/{job_id}  — Poll pipeline progress
GET  /api/v1/results/{job_id} — Retrieve completed prediction
GET  /api/v1/health            — Liveness / readiness probe
"""

import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import redis
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.api.schemas import (
    ClinicalParams,
    JobStatus,
    PredictionResult,
    UploadResponse,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import RateLimiter, sanitize_clinical_params, validate_fastq_file

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1")

# ── Redis & Rate Limiter Singletons ────────────────────────────────────

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Lazily create and return a Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _get_rate_limiter() -> RateLimiter:
    """Return a rate limiter instance bound to the Redis client."""
    return RateLimiter(_get_redis(), max_requests=30, window_seconds=60)


# ── Upload Directory ───────────────────────────────────────────────────

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Endpoints ──────────────────────────────────────────────────────────


@router.post("/upload", response_model=UploadResponse)
async def upload(
    request: Request,
    fastq: UploadFile = File(..., description="FASTQ file (.fq / .fastq)"),
    clinical_params: str = Form(..., description="JSON string of ClinicalParams"),
) -> UploadResponse:
    """Accept a FASTQ upload and enqueue the prediction pipeline.

    Returns a ``job_id`` that can be used to poll status and retrieve
    results via the ``/status`` and ``/results`` endpoints.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting.
    if not _get_rate_limiter().is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    # ── Validate FASTQ file ────────────────────────────────────────────
    file_content = await fastq.read()
    is_valid, error_msg = validate_fastq_file(file_content)
    if not is_valid:
        logger.warning(f"FASTQ validation failed: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    # ── Parse & validate clinical params ───────────────────────────────
    try:
        raw_params = json.loads(clinical_params)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"clinical_params is not valid JSON: {exc}",
        ) from exc

    cleaned_params = sanitize_clinical_params(raw_params)

    # ── Persist uploaded file ──────────────────────────────────────────
    job_id = str(uuid.uuid4())
    upload_subdir = UPLOAD_DIR / job_id
    upload_subdir.mkdir(parents=True, exist_ok=True)
    fastq_path = upload_subdir / fastq.filename

    with open(fastq_path, "wb") as fh:
        fh.write(file_content)

    # ── Audit log ──────────────────────────────────────────────────────
    logger.info(
        f"Upload accepted: job_id={job_id}, file={fastq.filename}, "
        f"size={len(file_content)}, fibrosis_stage={cleaned_params['fibrosis_stage']}, "
        f"age={cleaned_params['age']}, client_ip={client_ip}",
    )

    # ── Enqueue Celery task ────────────────────────────────────────────
    from app.tasks.pipeline_tasks import run_pipeline

    run_pipeline.delay(
        job_id=job_id,
        fastq_path=str(fastq_path),
        clinical_params=cleaned_params,
    )

    return UploadResponse(job_id=job_id, status="pending")


@router.get("/status/{job_id}", response_model=JobStatus)
async def job_status(job_id: str) -> JobStatus:
    """Return the current progress of an asynchronous pipeline job.

    Raises 404 if the job ID does not exist in Redis.
    """
    r = _get_redis()
    status_key = f"job:{job_id}:status"
    raw = r.get(status_key)

    if raw is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Corrupted status data for job {job_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Internal error reading job status",
        ) from exc

    return JobStatus(**data)


@router.get("/results/{job_id}", response_model=PredictionResult)
async def job_results(job_id: str) -> PredictionResult:
    """Return the full prediction result for a completed job.

    Raises 404 if the result is not yet available or the job does
    not exist.
    """
    r = _get_redis()
    result_key = f"job:{job_id}:result"
    status_key = f"job:{job_id}:status"

    raw_status = r.get(status_key)
    if raw_status is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        status_data = json.loads(raw_status)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Internal error") from exc

    if status_data.get("status") != "completed":
        raise HTTPException(
            status_code=202,
            detail=(
                f"Job {job_id} has not completed yet "
                f"(current status: {status_data.get('status')})"
            ),
        )

    raw_result = r.get(result_key)
    if raw_result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Result data for job {job_id} is not available",
        )

    try:
        result_data = json.loads(raw_result)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal error reading results",
        ) from exc

    logger.info(f"Results served for job_id={job_id}")
    return PredictionResult(**result_data)


@router.get("/health")
async def health() -> dict:
    """Liveness and readiness probe.

    Checks Redis connectivity and returns version information.
    """
    health_status = {"status": "ok", "version": "1.0.0"}

    try:
        r = _get_redis()
        r.ping()
        health_status["redis"] = "connected"
    except redis.RedisError:
        health_status["redis"] = "disconnected"
        health_status["status"] = "degraded"

    return health_status