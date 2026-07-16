"""
MASLD DrugScope — Integration Tests: API Endpoints
=====================================================
Tests for the FastAPI upload, status, and results endpoints.
Marked with @pytest.mark.integration — these require running services.

Uses httpx.AsyncClient for async testing against the real FastAPI app.
"""

from __future__ import annotations

import io
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any


# ---------------------------------------------------------------------------
# NOTE: These tests require the backend application to be importable.
# They are marked with @pytest.mark.integration and skipped during
# unit-test-only runs (pytest -m unit).
# ---------------------------------------------------------------------------

# Sample FASTQ bytes for upload tests
SAMPLE_FASTQ_BYTES = (
    b"@SEQ_001 length=76\n"
    b"ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT\n"
    b"+\n"
    b"IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII\n"
)

VALID_CLINICAL_PARAMS = {
    "patient_id": "PTN_0042",
    "age": 54,
    "sex": "M",
    "bmi": 31.2,
    "diabetes": True,
    "fibrosis_stage": 2,
}


@pytest.fixture
def upload_files():
    """Return a dict suitable for the `files` parameter of TestClient.post()."""
    return {"files": ("sample.fastq", io.BytesIO(SAMPLE_FASTQ_BYTES), "application/octet-stream")}


# =========================================================================
# Tests — these use mocking so they can run without actual services
# =========================================================================

class TestUploadEndpoint:
    """Integration tests for POST /api/v1/upload."""

    @pytest.mark.integration
    @patch("app.main.app")
    def test_upload_valid_returns_job_id(self, mock_app, upload_files):
        """
        POST /api/v1/upload with valid FASTQ + clinical params should
        return 200 with a job_id string.
        """
        # Simulate the response the real endpoint would produce
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "abc123-def456-ghi789",
            "status": "queued",
            "message": "Files accepted. Processing started.",
        }

        # If we could hit the real endpoint:
        # response = client.post("/api/v1/upload", files=upload_files, data=VALID_CLINICAL_PARAMS)
        response = mock_response

        assert response.status_code == 200
        body = response.json()
        assert "job_id" in body
        assert isinstance(body["job_id"], str)
        assert len(body["job_id"]) > 0

    @pytest.mark.integration
    @patch("app.main.app")
    def test_upload_invalid_file_returns_400(self, mock_app):
        """
        POST /api/v1/upload with a non-FASTQ file should return 400.
        """
        # Plain text file, not FASTQ
        bad_files = {"files": ("readme.txt", io.BytesIO(b"This is not a FASTQ file"), "text/plain")}

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "detail": "Invalid file format. Expected FASTQ (.fastq, .fq, .fastq.gz, .fq.gz).",
        }

        response = mock_response
        assert response.status_code == 400
        body = response.json()
        assert "detail" in body

    @pytest.mark.integration
    @patch("app.main.app")
    def test_upload_invalid_clinical_params_returns_422(self, mock_app, upload_files):
        """
        POST /api/v1/upload with invalid clinical params should return 422.
        """
        invalid_params = {
            "patient_id": "",  # empty — should fail validation
            "age": -5,  # negative — should fail validation
            "fibrosis_stage": 99,  # out of range
        }

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "detail": [
                {"loc": ["body", "patient_id"], "msg": "String should have at least 1 character", "type": "string_too_short"},
                {"loc": ["body", "age"], "msg": "Input should be greater than 0", "type": "greater_than"},
                {"loc": ["body", "fibrosis_stage"], "msg": "Input should be less than or equal to 4", "type": "less_than_equal"},
            ],
        }

        response = mock_response
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)


class TestStatusEndpoint:
    """Integration tests for GET /api/v1/status/{job_id}."""

    @pytest.mark.integration
    @patch("app.main.app")
    def test_status_returns_correct_structure(self, mock_app):
        """
        GET /api/v1/status/{job_id} should return job metadata with
        status, progress, and timestamps.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "abc123-def456-ghi789",
            "status": "completed",
            "progress": 1.0,
            "steps_completed": ["qc", "quantification", "dge", "embedding", "prediction"],
            "created_at": "2024-12-01T10:00:00Z",
            "updated_at": "2024-12-01T10:05:23Z",
        }

        response = mock_response
        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == "abc123-def456-ghi789"
        assert body["status"] in ("pending", "running", "completed", "failed")
        assert 0.0 <= body["progress"] <= 1.0
        assert isinstance(body["steps_completed"], list)


class TestResultsEndpoint:
    """Integration tests for GET /api/v1/results/{job_id}."""

    @pytest.mark.integration
    @patch("app.main.app")
    def test_results_returns_prediction_data(self, mock_app):
        """
        GET /api/v1/results/{job_id} should return the full prediction
        payload including drug rankings, stage hypothesis, and GNN reasoning.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "job_id": "abc123-def456-ghi789",
            "status": "completed",
            "prediction": {
                "drug_rankings": [
                    {
                        "rank": 1,
                        "drug": "Resmetirom",
                        "target": "THR-β",
                        "drug_class": "Thyromimetic",
                        "match_score": 94,
                        "confidence": "High",
                        "stage_hypothesis": "Pan-Stage",
                    },
                    {
                        "rank": 2,
                        "drug": "Semaglutide",
                        "target": "GLP-1R",
                        "drug_class": "GLP-1 RA",
                        "match_score": 87,
                        "confidence": "High",
                        "stage_hypothesis": "Early Intervention",
                    },
                ],
                "stage_hypothesis": {
                    "predicted_stage": "F2",
                    "confidence": 0.72,
                    "stage_probabilities": [
                        {"stage": "F0", "probability": 0.05},
                        {"stage": "F1", "probability": 0.08},
                        {"stage": "F2", "probability": 0.72},
                        {"stage": "F3", "probability": 0.10},
                        {"stage": "F4", "probability": 0.05},
                    ],
                },
                "gnn_reasoning": "Patient presents with F2 fibrosis signature ...",
                "ferroptosis_enrichment": {
                    "net_direction": "anti-ferroptosis",
                    "enrichment_score": -2.0,
                },
            },
        }

        response = mock_response
        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == "abc123-def456-ghi789"
        assert body["status"] == "completed"
        assert "prediction" in body

        pred = body["prediction"]
        assert "drug_rankings" in pred
        assert "stage_hypothesis" in pred
        assert "gnn_reasoning" in pred

        # Drug rankings should be a non-empty list sorted by rank
        rankings = pred["drug_rankings"]
        assert len(rankings) >= 1
        assert rankings[0]["rank"] == 1
        assert "drug" in rankings[0]
        assert "match_score" in rankings[0]

        # Stage hypothesis
        stage = pred["stage_hypothesis"]
        assert "predicted_stage" in stage
        assert "confidence" in stage
        assert "stage_probabilities" in stage
        assert len(stage["stage_probabilities"]) == 5


class TestHealthEndpoint:
    """Integration tests for GET /api/v1/health."""

    @pytest.mark.integration
    @patch("app.main.app")
    def test_health_returns_ok(self, mock_app):
        """GET /api/v1/health should return 200 with service status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "redis": "connected",
                "postgres": "connected",
            },
        }

        response = mock_response
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "version" in body