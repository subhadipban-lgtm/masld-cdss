"""
MASLD DrugScope — Shared Pytest Fixtures
=========================================
Common test fixtures used across all test modules.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# FASTQ fixture — a minimal but valid 4-line FASTQ entry (2 records)
# ---------------------------------------------------------------------------
SAMPLE_FASTQ_CONTENT = """\
@SEQ_001_001 length=76
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
@SEQ_001_002 length=76
TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCA
+
IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII
"""


@pytest.fixture
def sample_fastq_content() -> str:
    """Return a valid multi-record FASTQ string for testing."""
    return SAMPLE_FASTQ_CONTENT


@pytest.fixture
def sample_fastq_file(sample_fastq_content: str, tmp_path) -> str:
    """Write FASTQ content to a temp file and return the path."""
    f = tmp_path / "sample.fastq"
    f.write_text(sample_fastq_content)
    return str(f)


# ---------------------------------------------------------------------------
# Clinical parameters fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_clinical_params() -> Dict[str, Any]:
    """
    Return a valid ClinicalParams dict matching the Pydantic model used
    by the upload endpoint.
    """
    return {
        "patient_id": "PTN_0042",
        "age": 54,
        "sex": "M",
        "bmi": 31.2,
        "diabetes": True,
        "fibrosis_stage": 2,
        "ast": 67.0,
        "alt": 82.0,
        "platelet_count": 198000,
        "albumin": 3.8,
        "bilirubin": 1.1,
    }


# ---------------------------------------------------------------------------
# Mocked Redis client
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_redis() -> MagicMock:
    """Return a mocked Redis client suitable for patching."""
    redis = MagicMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.delete.return_value = True
    redis.exists.return_value = False
    redis.hset.return_value = True
    redis.hget.return_value = b'{"status": "pending"}'
    redis.lpush.return_value = 1
    redis.brpop.return_value = (b"celery", b'{"task_id": "abc-123"}')
    return redis


# ---------------------------------------------------------------------------
# Temporary upload directory
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_upload_dir(tmp_path) -> str:
    """Create (and yield) a temporary upload directory, cleaned up automatically."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return str(upload_dir)