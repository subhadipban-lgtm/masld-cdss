"""Celery task for the MASLD DrugScope prediction pipeline.

Orchestrates the full workflow:
  1. FastQC quality control (0–15%)
  2. fastp trimming (15–30%)
  3. Salmon quantification (30–60%)
  4. Differential gene expression (60–80%)
  5. GNN inference & drug ranking (80–95%)
  6. Store results in Redis (95–100%)
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import redis
import torch
import numpy as np
from celery import Celery

from app.api.schemas import ClinicalParams
from app.core.config import settings
from app.core.logging import get_logger
from app.gnn.embeddings import compute_patient_embeddings, load_normalization_stats
from app.gnn.model import GraphSAGE, load_pretrained_weights
from app.gnn.predict import (
    generate_attention_weights,
    generate_reasoning_summary,
    generate_stage_hypotheses,
    personalize_drugs,
    rank_drugs,
)
from app.kg.builder import KnowledgeGraph
from app.kg.ontologies import OntologyMapper
from app.pipeline.dge import (
    compute_ferroptosis_signature,
    filter_significant_genes,
    run_differential_expression,
)
from app.pipeline.fastq_processor import run_fastp, run_fastqc, validate_fastq_structure
from app.pipeline.quantification import run_salmon_quant

logger = get_logger(__name__)

# ── Celery App ──────────────────────────────────────────────────────────

celery_app = Celery(
    "masld_drugscope",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Redis Helper ────────────────────────────────────────────────────────


def _get_redis() -> redis.Redis:
    """Return a synchronous Redis client."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def _update_status(
    job_id: str,
    status: str,
    current_step: str,
    progress: float,
    eta_seconds: float | None = None,
    error: str | None = None,
) -> None:
    """Write the current job status to Redis."""
    r = _get_redis()
    payload = {
        "job_id": job_id,
        "status": status,
        "current_step": current_step,
        "progress": progress,
        "eta_seconds": eta_seconds,
        "error": error,
        "started_at": datetime.now(timezone.utc).isoformat() if progress > 0 else None,
        "completed_at": None,
    }
    r.setex(
        f"job:{job_id}:status",
        settings.upload_cleanup_hours * 3600,
        json.dumps(payload),
    )


def _estimate_eta(start_time: float, progress: float) -> float | None:
    """Estimate remaining seconds based on elapsed time and progress."""
    if progress <= 0:
        return None
    elapsed = time.time() - start_time
    return (elapsed / progress) * (100 - progress)


# ── Main Pipeline Task ──────────────────────────────────────────────────


@celery_app.task(bind=True, name="run_pipeline")
def run_pipeline(
    self,
    job_id: str,
    fastq_path: str,
    clinical_params: dict,
) -> str:
    """Execute the full MASLD prediction pipeline.

    Parameters
    ----------
    self:
        Celery task instance (for ``self.update_state``).
    job_id:
        Unique job identifier.
    fastq_path:
        Path to the uploaded FASTQ file.
    clinical_params:
        Validated clinical parameter dict.

    Returns
    -------
    str
        The ``job_id``.
    """
    start_time = time.time()
    r = _get_redis()
    params = ClinicalParams(**clinical_params)
    work_dir = Path(f"/app/workdir/{job_id}")
    work_dir.mkdir(parents=True, exist_ok=True)

    has_fastq = True
    dge_results = None
    dge_stats: dict = {
        "n_total": 0,
        "n_significant": 0,
        "ferroptosis_directionality": "mixed",
    }

    try:
        # ── Step 1: Quality Control (0–15%) ────────────────────────────
        _update_status(job_id, "quality_control", "Running FastQC", 0)
        logger.info(f"[{job_id}] Step 1/5: Quality control")

        if not validate_fastq_structure(fastq_path):
            raise RuntimeError("Uploaded file failed FASTQ structure validation")

        fastqc_dir = str(work_dir / "fastqc")
        fastqc_metrics = run_fastqc(fastq_path, fastqc_dir, job_id=job_id)

        _update_status(
            job_id, "quality_control", "FastQC complete",
            15, _estimate_eta(start_time, 15),
        )

        # ── Step 2: Trimming (15–30%) ──────────────────────────────────
        logger.info(f"[{job_id}] Step 2/5: Trimming with fastp")

        fastp_dir = str(work_dir / "fastp")
        trimmed_fastq, fastp_metrics = run_fastp(
            fastq_path, fastp_dir, job_id=job_id
        )

        _update_status(
            job_id, "trimming", "fastp complete",
            30, _estimate_eta(start_time, 30),
        )

        # ── Step 3: Quantification (30–60%) ────────────────────────────
        logger.info(f"[{job_id}] Step 3/5: Salmon quantification")

        salmon_dir = str(work_dir / "salmon")
        quant_dir, gene_counts_df = run_salmon_quant(
            trimmed_fastq,
            str(settings.salmon_index_path),
            salmon_dir,
            job_id=job_id,
        )

        _update_status(
            job_id, "quantifying", "Salmon complete",
            60, _estimate_eta(start_time, 60),
        )

        # ── Step 4: Differential Expression (60–80%) ───────────────────
        logger.info(f"[{job_id}] Step 4/5: Differential expression analysis")

        ref_metadata = str(
            settings.reference_data_path / "reference_metadata.csv"
        )
        dge_results = run_differential_expression(
            gene_counts_df, params, ref_metadata
        )

        sig_genes = filter_significant_genes(dge_results)
        ferroptosis = compute_ferroptosis_signature(dge_results)

        dge_stats = {
            "n_total": len(dge_results),
            "n_significant": len(sig_genes),
            "ferroptosis_directionality": ferroptosis["directionality"],
            "n_ferroptosis_genes": ferroptosis["n_significant"],
        }

        _update_status(
            job_id, "dge_analysis", "DGE complete",
            80, _estimate_eta(start_time, 80),
        )

        # ── Step 5: GNN Inference (80–95%) ──────────────────────────────
        logger.info(f"[{job_id}] Step 5/5: GNN inference")

        # Load knowledge graph.
        kg = KnowledgeGraph(settings.kg_edge_list_path)
        kg_stats = kg.get_stats()
        logger.info(f"[{job_id}] KG loaded: {kg_stats}")

        # Load ontology mapper.
        onto = OntologyMapper(str(settings.reference_data_path))

        # Build node features (identity-based, shape N×N).
        n_nodes = kg.get_node_count()
        feature_dim = n_nodes
        node_features = torch.eye(n_nodes, dtype=torch.float32)

        # Load normalization stats.
        try:
            norm_stats = load_normalization_stats(settings.normalization_stats_path)
        except FileNotFoundError:
            # Fallback: unit normalization.
            norm_stats = {
                "mean": np.zeros(feature_dim, dtype=np.float32),
                "std": np.ones(feature_dim, dtype=np.float32),
            }
            logger.warning("Normalization stats not found; using identity normalization")

        # Build patient DGE dict for gene embedding injection.
        patient_dge: dict[str, float] = {}
        if dge_results is not None and not dge_results.empty:
            for _, row in dge_results.head(200).iterrows():
                patient_dge[row["gene"]] = float(row["log2FC"])

        gene_indices = kg.get_gene_indices()
        drug_indices = kg.get_drug_indices()

        # Initialise model.
        # Feature dim is clamped to a manageable size for the GNN.
        gnn_in_dim = min(feature_dim, 128)
        gnn_hidden_dim = 64
        gnn_out_dim = 32

        model = GraphSAGE(gnn_in_dim, gnn_hidden_dim, gnn_out_dim)

        # Project node_features if N > 128 using a random projection.
        if feature_dim > gnn_in_dim:
            torch.manual_seed(42)
            projection = torch.randn(feature_dim, gnn_in_dim)
            node_features = node_features @ projection

        load_pretrained_weights(model, settings.model_weights_path)

        # Compute embeddings.
        embeddings = compute_patient_embeddings(
            model, node_features, kg.get_edge_index(), gene_indices, patient_dge
        )

        # Rank drugs.
        ranked_drugs = rank_drugs(embeddings, drug_indices)
        ranked_drugs = personalize_drugs(params, has_fastq, ranked_drugs)

        # Stage hypotheses.
        stage_hypotheses = generate_stage_hypotheses(
            params.fibrosis_stage, has_fastq
        )

        # Attention weights.
        gene_names = kg.get_gene_names()
        attention_weights = generate_attention_weights(embeddings, gene_names)

        # Reasoning summary.
        top_drug = ranked_drugs[0] if ranked_drugs else {}
        reasoning = generate_reasoning_summary(
            params, top_drug, dge_stats, kg_stats, has_fastq
        )

        # ── Build final result ──────────────────────────────────────────
        execution_time = time.time() - start_time

        result = {
            "job_id": job_id,
            "drugs": ranked_drugs,
            "stage_hypotheses": stage_hypotheses,
            "reasoning_summary": reasoning,
            "attention_weights": attention_weights,
            "pipeline_version": settings.pipeline_version,
            "model_version": settings.model_version,
            "execution_time_seconds": round(execution_time, 2),
        }

        # Store in Redis.
        r.setex(
            f"job:{job_id}:result",
            settings.upload_cleanup_hours * 3600,
            json.dumps(result, default=str),
        )

        # Update status to completed.
        _update_status(
            job_id, "completed", "Pipeline finished",
            100, 0,
        )

        # Patch completed_at into status.
        status_payload = json.loads(r.get(f"job:{job_id}:status"))
        status_payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        r.setex(
            f"job:{job_id}:status",
            settings.upload_cleanup_hours * 3600,
            json.dumps(status_payload),
        )

        logger.info(
            f"[{job_id}] Pipeline completed in {execution_time:.1f}s — "
            f"{len(ranked_drugs)} drugs ranked, "
            f"top: {top_drug.get('drug', 'N/A')}"
        )

        return job_id

    except Exception as exc:
        # Mark job as failed.
        _update_status(
            job_id,
            "failed",
            f"Error in pipeline: {exc}",
            0,
            error=str(exc),
        )
        # Patch started_at.
        r2 = _get_redis()
        raw = r2.get(f"job:{job_id}:status")
        if raw:
            sp = json.loads(raw)
            sp["started_at"] = datetime.now(timezone.utc).isoformat()
            r2.setex(
                f"job:{job_id}:status",
                settings.upload_cleanup_hours * 3600,
                json.dumps(sp),
            )

        logger.error(f"[{job_id}] Pipeline failed: {exc}", exc_info=True)
        raise

    finally:
        # Cleanup work directory.
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        except Exception as cleanup_exc:
            logger.warning(f"[{job_id}] Cleanup failed: {cleanup_exc}")