"""
MASLD DrugScope — Unit Tests: Embedding Computation
=====================================================
Tests for feature normalization, cosine similarity ranking, and
stage hypothesis generation.
"""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any


# ---------------------------------------------------------------------------
# Standalone implementations mirroring production code.
# Swap imports to `from app.services.embedding_service import …` when available.
# ---------------------------------------------------------------------------

def normalize_features(
    expression_matrix: np.ndarray,
    means: np.ndarray | None = None,
    stds: np.ndarray | None = None,
    epsilon: float = 1e-8,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Z-score normalize gene expression features.

    Parameters
    ----------
    expression_matrix : (n_samples, n_genes)
    means : optional pre-computed means; if None, compute from data
    stds  : optional pre-computed stds;  if None, compute from data

    Returns
    -------
    (normalized_matrix, means, stds)
    """
    if means is None:
        means = expression_matrix.mean(axis=0)
    if stds is None:
        stds = expression_matrix.std(axis=0, ddof=1)

    # Prevent division by zero for constant genes
    stds_safe = np.where(stds < epsilon, 1.0, stds)

    normalized = (expression_matrix - means) / stds_safe
    return normalized, means, stds


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(dot / (norm_a * norm_b))


def rank_drugs_by_similarity(
    patient_embedding: np.ndarray,
    drug_embeddings: Dict[str, np.ndarray],
) -> List[Tuple[str, float]]:
    """
    Rank drugs by cosine similarity to patient embedding.

    Returns list of (drug_name, similarity) sorted descending.
    """
    scores = []
    for drug_name, drug_emb in drug_embeddings.items():
        sim = cosine_similarity(patient_embedding, drug_emb)
        scores.append((drug_name, sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def generate_stage_hypothesis(
    patient_embedding: np.ndarray,
    stage_centroids: Dict[str, np.ndarray],
) -> Dict[str, Any]:
    """
    Generate fibrosis stage hypothesis by comparing patient embedding
    to pre-computed stage centroids.

    Returns dict with stage probabilities, predicted stage, and confidence.
    """
    similarities = {}
    for stage, centroid in stage_centroids.items():
        similarities[stage] = cosine_similarity(patient_embedding, centroid)

    # Softmax-like normalization to get "probabilities"
    sims = np.array(list(similarities.values()))
    exp_sims = np.exp(sims * 5)  # temperature=5 for sharper distribution
    probs = exp_sims / exp_sims.sum()

    predicted_idx = int(np.argmax(probs))
    stages = list(similarities.keys())
    predicted_stage = stages[predicted_idx]
    confidence = float(probs[predicted_idx])

    stage_probs = [
        {"stage": s, "probability": round(float(p), 4), "label": f"Fibrosis {s}"}
        for s, p in zip(stages, probs)
    ]

    return {
        "predicted_stage": predicted_stage,
        "confidence": round(confidence, 4),
        "stage_probabilities": stage_probs,
    }


# =========================================================================
# Tests
# =========================================================================

class TestEmbedding:
    """Unit tests for embedding computation and similarity ranking."""

    @pytest.mark.unit
    def test_normalize_features_produces_correct_zscores(self):
        """
        Z-score normalization should produce mean≈0 and std≈1 per gene column.
        """
        np.random.seed(42)
        # 20 samples, 50 genes
        X = np.random.randn(20, 50) * 5 + 10

        X_norm, means, stds = normalize_features(X)

        # Each gene column should have mean ≈ 0 and std ≈ 1
        col_means = X_norm.mean(axis=0)
        col_stds = X_norm.std(axis=0, ddof=1)

        np.testing.assert_allclose(col_means, 0.0, atol=1e-10)
        np.testing.assert_allclose(col_stds, 1.0, atol=1e-10)

    @pytest.mark.unit
    def test_normalize_features_with_precomputed_stats(self):
        """Normalization with pre-computed means/stds should still be valid."""
        X = np.array([[10, 20], [12, 22], [14, 24]], dtype=float)
        means = np.array([12.0, 22.0])
        stds = np.array([2.0, 2.0])

        X_norm, _, _ = normalize_features(X, means=means, stds=stds)

        expected = np.array([[-1.0, -1.0], [0.0, 0.0], [1.0, 1.0]])
        np.testing.assert_allclose(X_norm, expected, atol=1e-10)

    @pytest.mark.unit
    def test_normalize_features_constant_gene(self):
        """Constant genes (std=0) should not cause division by zero."""
        X = np.array([[5, 5, 3], [5, 7, 5], [5, 9, 7]], dtype=float)
        X_norm, _, _ = normalize_features(X)
        assert not np.any(np.isnan(X_norm))
        assert not np.any(np.isinf(X_norm))

    @pytest.mark.unit
    def test_cosine_similarity_identical_vectors(self):
        """Cosine similarity of a vector with itself should be 1.0."""
        v = np.array([1.0, 2.0, 3.0])
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-10

    @pytest.mark.unit
    def test_cosine_similarity_orthogonal_vectors(self):
        """Orthogonal vectors should have cosine similarity ≈ 0."""
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        assert abs(cosine_similarity(v1, v2) - 0.0) < 1e-10

    @pytest.mark.unit
    def test_cosine_similarity_opposite_vectors(self):
        """Opposite vectors should have cosine similarity ≈ -1.0."""
        v1 = np.array([1.0, 2.0, 3.0])
        v2 = np.array([-1.0, -2.0, -3.0])
        assert abs(cosine_similarity(v1, v2) - (-1.0)) < 1e-10

    @pytest.mark.unit
    def test_cosine_similarity_zero_vector(self):
        """Zero vector should return 0.0 similarity."""
        v1 = np.array([1.0, 2.0, 3.0])
        v2 = np.array([0.0, 0.0, 0.0])
        assert cosine_similarity(v1, v2) == 0.0

    @pytest.mark.unit
    def test_ranking_produces_correct_order(self):
        """
        Drug ranking should sort by descending cosine similarity.
        """
        np.random.seed(42)
        patient = np.random.randn(50)

        # Drug A is aligned with patient, Drug B is opposite, Drug C is orthogonal
        drug_a = patient + np.random.randn(50) * 0.1  # very similar
        drug_b = -patient + np.random.randn(50) * 0.1  # opposite
        drug_c = np.random.randn(50)  # random

        drug_embeddings = {
            "Drug_B": drug_b,
            "Drug_A": drug_a,
            "Drug_C": drug_c,
        }

        ranking = rank_drugs_by_similarity(patient, drug_embeddings)

        names = [r[0] for r in ranking]
        scores = [r[1] for r in ranking]

        assert names[0] == "Drug_A"
        assert scores[0] > scores[1]  # Drug_A > Drug_B or Drug_C
        # Drug_B should be last (opposite direction → negative similarity)
        assert scores[-1] < 0

    @pytest.mark.unit
    def test_stage_hypothesis_returns_structure(self):
        """Stage hypothesis should return predicted_stage, confidence, and probabilities."""
        np.random.seed(42)
        patient = np.random.randn(50)

        stage_centroids = {
            "F0": np.random.randn(50) * 0.5,
            "F1": np.random.randn(50) * 0.5,
            "F2": patient + np.random.randn(50) * 0.1,  # most similar
            "F3": np.random.randn(50) * 0.5,
            "F4": np.random.randn(50) * 0.5,
        }

        result = generate_stage_hypothesis(patient, stage_centroids)

        assert "predicted_stage" in result
        assert "confidence" in result
        assert "stage_probabilities" in result
        assert result["predicted_stage"] == "F2"
        assert 0 < result["confidence"] <= 1.0
        assert len(result["stage_probabilities"]) == 5

        # Probabilities should sum to ~1.0
        total_prob = sum(s["probability"] for s in result["stage_probabilities"])
        assert abs(total_prob - 1.0) < 1e-6

    @pytest.mark.unit
    def test_stage_hypothesis_most_similar_stage_wins(self):
        """The stage with the highest cosine similarity should be predicted."""
        np.random.seed(99)
        patient = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

        stage_centroids = {
            "F0": np.array([5.0, 4.0, 3.0, 2.0, 1.0]),  # opposite direction
            "F3": np.array([1.1, 2.1, 3.1, 4.1, 5.1]),  # most similar
            "F4": np.array([0.0, 0.0, 0.0, 0.0, 0.0]),  # very different
        }

        result = generate_stage_hypothesis(patient, stage_centroids)
        assert result["predicted_stage"] == "F3"