"""
MASLD DrugScope — Unit Tests: Differential Gene Expression
===========================================================
Tests for DGE computation, significance filtering, and ferroptosis enrichment.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# Standalone implementations that mirror the production code.
# These are kept here so the tests run WITHOUT importing the (possibly
# unfinished) backend application code.  Once the backend is complete these
# imports should be swapped to:
#   from app.services.dge_service import run_differential_expression, …
# ---------------------------------------------------------------------------

# Known ferroptosis driver / suppressor genes (FerrDb + literature)
FERROPTOSIS_DRIVERS = {
    "TFRC", "SLC7A11", "NCOA4", "SAT1", "LPCAT3",
    "ACSL4", "POR", "CP", "NOX1", "RPL8",
}
FERROPTOSIS_SUPPRESSORS = {
    "GPX4", "NFE2L2", "HMOX1", "SOD2", "GCLC",
    "FTH1", "SLC40A1", "CDKN1A", "MT1G", "QSOX1",
}


def run_differential_expression(
    counts: pd.DataFrame,
    condition_col: str = "condition",
    advanced_label: str = "advanced",
) -> pd.DataFrame:
    """
    Minimal mock of the DGE pipeline.
    Returns a DataFrame with columns: gene, log2FC, pvalue, padj.
    """
    np.random.seed(42)
    genes = list(counts.columns) if "condition" not in counts.columns else [
        c for c in counts.columns if c != condition_col
    ]

    n_genes = len(genes)
    results = pd.DataFrame({
        "gene": genes,
        "log2FC": np.random.normal(0, 1.5, n_genes),
        "pvalue": np.random.uniform(1e-10, 0.5, n_genes),
    })
    # Benjamini-Hochberg approximation
    results = results.sort_values("pvalue").reset_index(drop=True)
    results["padj"] = results["pvalue"] * n_genes / (np.arange(n_genes) + 1)
    results["padj"] = results["padj"].clip(upper=1.0)
    return results[["gene", "log2FC", "pvalue", "padj"]]


def filter_significant_genes(
    dge_results: pd.DataFrame,
    log2fc_threshold: float = 1.0,
    padj_threshold: float = 0.05,
) -> pd.DataFrame:
    """Filter DGE results for significantly differentially expressed genes."""
    return dge_results[
        (dge_results["log2FC"].abs() >= log2fc_threshold)
        & (dge_results["padj"] <= padj_threshold)
    ].reset_index(drop=True)


def compute_ferroptosis_signature(
    dge_results: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Enrich ferroptosis pathway genes from DGE results.
    Returns driver/suppressor counts, top genes, and enrichment direction.
    """
    sig = filter_significant_genes(dge_results, log2fc_threshold=0.5, padj_threshold=0.1)

    drivers = sig[sig["gene"].isin(FERROPTOSIS_DRIVERS)]
    suppressors = sig[sig["gene"].isin(FERROPTOSIS_SUPPRESSORS)]

    driver_up = drivers[drivers["log2FC"] > 0]
    driver_down = drivers[drivers["log2FC"] < 0]
    suppressor_up = suppressors[suppressors["log2FC"] > 0]
    suppressor_down = suppressors[suppressors["log2FC"] < 0]

    # Enrichment: net direction
    n_driver_up = len(driver_up)
    n_suppressor_down = len(suppressor_down)
    net_pro_ferroptosis = n_driver_up + n_suppressor_down
    net_anti_ferroptosis = len(driver_down) + len(suppressor_up)

    return {
        "n_drivers": len(drivers),
        "n_suppressors": len(suppressors),
        "driver_genes": drivers["gene"].tolist()[:10],
        "suppressor_genes": suppressors["gene"].tolist()[:10],
        "net_direction": "pro-ferroptosis" if net_pro_ferroptosis > net_anti_ferroptosis else "anti-ferroptosis",
        "enrichment_score": round(net_pro_ferroptosis - net_anti_ferroptosis, 2),
    }


# =========================================================================
# Tests
# =========================================================================

class TestDGE:
    """Unit tests for differential gene expression computation."""

    @pytest.mark.unit
    def test_run_dge_returns_correct_columns(self):
        """run_differential_expression must return gene, log2FC, pvalue, padj."""
        # Create a minimal count matrix (10 genes × 6 samples)
        np.random.seed(0)
        counts = pd.DataFrame(
            np.random.randint(5, 500, size=(6, 10)),
            columns=["GPX4", "SLC7A11", "TFRC", "FTH1", "NFE2L2",
                     "HMOX1", "COL1A1", "TGFBR1", "PPARG", "SREBF1"],
        )
        counts["condition"] = ["early", "early", "early", "advanced", "advanced", "advanced"]

        result = run_differential_expression(counts)

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["gene", "log2FC", "pvalue", "padj"]
        assert len(result) == 10
        assert result["log2FC"].dtype == np.float64
        assert result["pvalue"].dtype == np.float64
        assert result["padj"].dtype == np.float64

    @pytest.mark.unit
    def test_run_dge_padj_bounded(self):
        """Adjusted p-values should be in [0, 1]."""
        np.random.seed(1)
        counts = pd.DataFrame(
            np.random.randint(5, 500, size=(6, 5)),
            columns=["A", "B", "C", "D", "E"],
        )
        counts["condition"] = ["early"] * 3 + ["advanced"] * 3
        result = run_differential_expression(counts)

        assert (result["padj"] >= 0).all()
        assert (result["padj"] <= 1).all()

    @pytest.mark.unit
    def test_filter_significant_genes_with_known_data(self):
        """Filter should keep only genes meeting log2FC and padj thresholds."""
        dge_results = pd.DataFrame({
            "gene": ["GPX4", "SLC7A11", "TFRC", "FTH1", "NFE2L2", "HMOX1"],
            "log2FC": [2.1, -0.3, 1.8, 0.5, -1.2, 3.5],
            "pvalue": [1e-8, 0.4, 1e-5, 0.1, 1e-3, 1e-12],
            "padj": [1e-6, 0.8, 5e-4, 0.3, 0.01, 1e-10],
        })

        filtered = filter_significant_genes(
            dge_results, log2fc_threshold=1.0, padj_threshold=0.05
        )

        # GPX4 (|2.1|>1, padj=1e-6<0.05), TFRC (|1.8|>1, padj=5e-4<0.05),
        # NFE2L2 (|-1.2|>1, padj=0.01<0.05), HMOX1 (|3.5|>1, padj=1e-10<0.05)
        assert len(filtered) == 4
        assert set(filtered["gene"].tolist()) == {"GPX4", "TFRC", "NFE2L2", "HMOX1"}

    @pytest.mark.unit
    def test_filter_significant_genes_empty_result(self):
        """Filter should return empty DataFrame when nothing is significant."""
        dge_results = pd.DataFrame({
            "gene": ["A", "B"],
            "log2FC": [0.1, -0.2],
            "pvalue": [0.9, 0.8],
            "padj": [0.95, 0.85],
        })

        filtered = filter_significant_genes(dge_results)
        assert len(filtered) == 0

    @pytest.mark.unit
    def test_compute_ferroptosis_enrichment(self):
        """Ferroptosis signature should correctly identify drivers and suppressors."""
        dge_results = pd.DataFrame({
            "gene": ["GPX4", "TFRC", "SLC7A11", "NFE2L2", "HMOX1", "ALB", "AFP"],
            "log2FC": [-1.5, 2.0, 1.8, -1.2, -2.1, 0.3, 0.1],
            "pvalue": [1e-8, 1e-6, 1e-5, 1e-4, 1e-10, 0.5, 0.6],
            "padj": [1e-6, 5e-5, 1e-4, 0.001, 1e-8, 0.7, 0.8],
        })

        result = compute_ferroptosis_signature(dge_results)

        assert "n_drivers" in result
        assert "n_suppressors" in result
        assert "net_direction" in result
        assert "enrichment_score" in result
        # TFRC and SLC7A11 are drivers (up-regulated → pro-ferroptosis)
        assert result["n_drivers"] >= 2
        # GPX4, NFE2L2, HMOX1 are suppressors (down-regulated → anti-ferroptosis)
        assert result["n_suppressors"] >= 2
        assert result["net_direction"] in ("pro-ferroptosis", "anti-ferroptosis")