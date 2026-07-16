"""Security utilities for the MASLD DrugScope API.

Provides FASTQ file validation, clinical-parameter sanitization, a
Redis-backed token-bucket rate limiter, and CORS middleware configuration.
"""

import time
import uuid
from typing import Any

import redis
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── FASTQ Validation ───────────────────────────────────────────────────

FASTQ_MAGIC_PREFIXES = (b"@CL", b"@HWI", b"@A00", b"@D00", b"@K00", b"@N00", b"@E00")


def validate_fastq_file(file_content: bytes) -> tuple[bool, str]:
    """Validate raw uploaded file content as a FASTQ file.

    Checks:
    1. File size does not exceed ``MAX_UPLOAD_SIZE_MB``.
    2. The file starts with a recognised FASTQ header prefix.

    Parameters
    ----------
    file_content:
        Raw bytes of the uploaded file.

    Returns
    -------
    (is_valid, message)
        ``True`` with an empty message on success; ``False`` with a
        human-readable reason on failure.
    """
    if len(file_content) > settings.max_upload_size_bytes:
        max_mb = settings.max_upload_size_mb
        return False, f"File exceeds maximum upload size of {max_mb} MB"

    if len(file_content) == 0:
        return False, "Uploaded file is empty"

    first_line = file_content.split(b"\n", 1)[0].strip()
    if not any(first_line.startswith(prefix) for prefix in FASTQ_MAGIC_PREFIXES):
        return False, (
            "File does not appear to be a valid FASTQ file "
            "(unrecognised header prefix)"
        )

    return True, ""


# ── Clinical Parameter Sanitization ────────────────────────────────────

ALLOWED_CLINICAL_KEYS = {"age", "fibrosis_stage", "bmi", "alt", "ast", "hba1c"}


def sanitize_clinical_params(params: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize clinical input parameters.

    Parameters
    ----------
    params:
        Raw dictionary parsed from the JSON form field.

    Returns
    -------
    dict
        A dictionary containing only the allowed keys with values
        coerced to the expected numeric types.

    Raises
    ------
    HTTPException (400)
        If required fields are missing or values are out of range.
    """
    if not isinstance(params, dict):
        raise HTTPException(status_code=400, detail="clinical_params must be a JSON object")

    # Required fields.
    if "age" not in params:
        raise HTTPException(status_code=400, detail="Missing required field: age")
    if "fibrosis_stage" not in params:
        raise HTTPException(status_code=400, detail="Missing required field: fibrosis_stage")

    age = params["age"]
    if not isinstance(age, int | float):
        raise HTTPException(status_code=400, detail="age must be a number")
    if not (18 <= age <= 85):
        raise HTTPException(status_code=400, detail="age must be between 18 and 85")

    fibrosis = params["fibrosis_stage"]
    if not isinstance(fibrosis, int | float):
        raise HTTPException(status_code=400, detail="fibrosis_stage must be an integer")
    if not (0 <= fibrosis <= 4):
        raise HTTPException(status_code=400, detail="fibrosis_stage must be between 0 and 4")

    sanitized: dict[str, Any] = {
        "age": int(age),
        "fibrosis_stage": int(fibrosis),
    }

    # Optional fields.
    optional_ranges: dict[str, tuple[float, float]] = {
        "bmi": (15, 60),
        "alt": (0, 5000),
        "ast": (0, 5000),
        "hba1c": (3, 20),
    }
    for key, (lo, hi) in optional_ranges.items():
        value = params.get(key)
        if value is not None:
            if not isinstance(value, int | float):
                raise HTTPException(
                    status_code=400,
                    detail=f"{key} must be a number",
                )
            if not (lo <= value <= hi):
                raise HTTPException(
                    status_code=400,
                    detail=f"{key} must be between {lo} and {hi}",
                )
            sanitized[key] = float(value)

    logger.info("Sanitized clinical params", extra={"job_id": None})
    return sanitized


# ── Token-Bucket Rate Limiter ──────────────────────────────────────────

class RateLimiter:
    """Redis-backed token-bucket rate limiter.

    Parameters
    ----------
    redis_client:
        Connected ``redis.Redis`` instance.
    max_requests:
        Maximum number of requests allowed in the window.
    window_seconds:
        Duration of the sliding window in seconds.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_requests: int = 30,
        window_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._max_requests = max_requests
        self._window = window_seconds

    def _bucket_key(self, client_ip: str) -> str:
        return f"ratelimit:upload:{client_ip}"

    def is_allowed(self, client_ip: str) -> bool:
        """Check whether a request from *client_ip* is within limits.

        Uses a sliding-window counter stored as a Redis sorted set
        where each member's score is the request timestamp.
        """
        key = self._bucket_key(client_ip)
        now = time.time()
        window_start = now - self._window

        try:
            pipe = self._redis.pipeline(transaction=False)
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(uuid.uuid4()): now})
            pipe.zcard(key)
            pipe.expire(key, self._window + 1)
            results = pipe.execute()
            current_count = results[2]
        except redis.RedisError as exc:
            logger.warning(f"Redis rate-limit check failed: {exc}")
            return True  # fail-open

        allowed = current_count <= self._max_requests
        if not allowed:
            logger.info(
                f"Rate limit exceeded for {client_ip}: {current_count}/{self._max_requests}"
            )
        return allowed


# ── CORS Middleware ────────────────────────────────────────────────────

def get_cors_middleware_kwargs() -> dict[str, Any]:
    """Return keyword arguments for ``CORSMiddleware`` configuration."""
    return {
        "allow_origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],
    }