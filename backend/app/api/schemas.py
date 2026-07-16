"""Pydantic v2 schemas for the MASLD DrugScope API.

All request/response models used by the FastAPI router are defined here.
"""

from typing import Literal

from pydantic import BaseModel, Field


# ── Request Schemas ────────────────────────────────────────────────────


class ClinicalParams(BaseModel):
    """Patient clinical parameters required for drug prediction.

    ``fibrosis_stage`` follows the EASL F0–F4 staging system.
    """

    age: int = Field(ge=18, le=85, description="Patient age in years")
    fibrosis_stage: int = Field(
        ge=0, le=4, description="Liver fibrosis stage (F0–F4)"
    )
    bmi: float | None = Field(
        default=None, ge=15, le=60, description="Body mass index (kg/m²)"
    )
    alt: float | None = Field(
        default=None, ge=0, le=5000, description="Alanine aminotransferase (U/L)"
    )
    ast: float | None = Field(
        default=None, ge=0, le=5000, description="Aspartate aminotransferase (U/L)"
    )
    hba1c: float | None = Field(
        default=None, ge=3, le=20, description="Glycated haemoglobin (%)"
    )


# ── Upload Response ────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Returned immediately after a FASTQ upload is accepted."""

    job_id: str
    status: str = "pending"


# ── Job Status ─────────────────────────────────────────────────────────


class JobStatus(BaseModel):
    """Progress and status of an asynchronous pipeline job."""

    job_id: str
    status: Literal[
        "pending",
        "quality_control",
        "trimming",
        "quantifying",
        "dge_analysis",
        "gnn_inference",
        "completed",
        "failed",
    ]
    current_step: str
    progress: float = Field(ge=0, le=100, description="Progress percentage (0–100)")
    eta_seconds: float | None = None
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


# ── Prediction Results ─────────────────────────────────────────────────


class TopTarget(BaseModel):
    """A gene target associated with a ranked drug."""

    gene: str
    logFC: float
    pValue: float


class DrugPredictionResponse(BaseModel):
    """A single ranked drug prediction with mechanistic annotations."""

    rank: int
    drug: str
    target: str
    drug_class: str
    approval_status: str
    match_score: float
    stage_hypothesis: str
    age_adjustment: str
    top_targets: list[dict]
    ferroptosis_relevance: str
    confidence: str
    is_novel_candidate: bool = False


class StageHypothesis(BaseModel):
    """Probability distribution over fibrosis stages F0–F4."""

    stage: str
    probability: float
    label: str


class AttentionWeight(BaseModel):
    """Per-gene attention weight across GNN layers."""

    gene: str
    layer1: float
    layer2: float


class PredictionResult(BaseModel):
    """Full prediction output returned once the pipeline completes."""

    job_id: str
    drugs: list[DrugPredictionResponse]
    stage_hypotheses: list[StageHypothesis]
    reasoning_summary: str
    attention_weights: list[dict]
    pipeline_version: str
    model_version: str
    execution_time_seconds: float