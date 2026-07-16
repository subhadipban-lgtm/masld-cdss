"""Patient-specific embedding computation for the MASLD GraphSAGE model.

Handles:
- Updating gene node features with patient DGE values
- Z-score normalisation using pre-computed global statistics
- Running the forward pass to produce node embeddings
"""

import json

import numpy as np
import torch

from app.core.logging import get_logger

logger = get_logger(__name__)


def compute_patient_embeddings(
    model: torch.nn.Module,
    node_features: torch.Tensor,
    edge_index: torch.Tensor,
    gene_indices: list[int],
    patient_dge: dict[str, float],
) -> torch.Tensor:
    """Compute node embeddings with patient-specific DGE features injected.

    The patient's DGE log2FC values are written into the gene-node
    rows of *node_features* (at the last feature dimension), then
    normalised and passed through the GNN.

    Parameters
    ----------
    model:
        A ``GraphSAGE`` model instance (in eval mode).
    node_features:
        Base feature matrix ``(N, D)`` for all nodes.
    edge_index:
        COO edge tensor ``(2, E)``.
    gene_indices:
        List of integer indices into *node_features* that correspond
        to gene nodes.
    patient_dge:
        Mapping ``gene_symbol -> log2FC`` for the patient.  Only genes
        present in this dict will be updated; others retain their
        base feature values.

    Returns
    -------
    torch.Tensor
        Node embeddings of shape ``(N, out_dim)``.
    """
    # Clone to avoid mutating the base features.
    features = node_features.clone()

    # Inject DGE values into the last feature slot of gene nodes.
    dge_values = np.array(list(patient_dge.values()), dtype=np.float32)
    if len(dge_values) > 0:
        dge_mean = np.mean(dge_values)
        dge_std = np.std(dge_values) + 1e-10
        normalised_dge = (dge_values - dge_mean) / dge_std

        for idx, gene_sym in zip(gene_indices, patient_dge.keys()):
            if idx < features.size(0):
                dge_idx = list(patient_dge.keys()).index(gene_sym)
                features[idx, -1] = normalised_dge[dge_idx]

    # Run forward pass with no gradient computation.
    with torch.no_grad():
        embeddings = model(features, edge_index)

    logger.info(
        f"Patient embeddings computed: shape={embeddings.shape}, "
        f"{len(gene_indices)} gene nodes updated with DGE"
    )
    return embeddings


def normalize_features(
    features: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
) -> np.ndarray:
    """Z-score normalise a feature matrix.

    Parameters
    ----------
    features:
        ``(N, D)`` array.
    mean:
        ``(D,)`` mean vector.
    std:
        ``(D,)`` standard-deviation vector.

    Returns
    -------
    np.ndarray
        Normalised ``(N, D)`` array.
    """
    std_safe = np.where(std == 0, 1.0, std)
    return (features - mean) / std_safe


def load_normalization_stats(path: str) -> dict:
    """Load pre-computed mean and standard-deviation arrays from JSON.

    Expected JSON structure::

        {
            "mean": [0.12, 0.34, ...],
            "std": [0.45, 0.67, ...]
        }

    Parameters
    ----------
    path:
        Path to the JSON file.

    Returns
    -------
    dict
        ``"mean"`` and ``"std"`` as numpy arrays.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Normalization stats not found at {path}")

    with open(p) as fh:
        data = json.load(fh)

    mean = np.array(data["mean"], dtype=np.float32)
    std = np.array(data["std"], dtype=np.float32)

    logger.info(f"Loaded normalization stats from {path}: mean shape={mean.shape}")
    return {"mean": mean, "std": std}