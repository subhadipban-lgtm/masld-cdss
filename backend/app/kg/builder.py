"""Knowledge graph builder for MASLD DrugScope.

Loads a pre-built edge list (TSV) and provides methods to extract
node features, convert to PyTorch tensors, compute statistics, and
extract subgraphs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

from app.core.logging import get_logger

logger = get_logger(__name__)


class KnowledgeGraph:
    """In-memory knowledge graph loaded from a TSV edge list.

    The edge list is expected to have at least three columns
    (no header by default):
        ``source_node_id``, ``target_node_id``, ``edge_type``

    Additional columns (e.g. ``weight``) are preserved.

    Parameters
    ----------
    edge_list_path:
        Path to the TSV edge list file.
    """

    def __init__(self, edge_list_path: str) -> None:
        self._edge_list_path = edge_list_path
        self._edges: pd.DataFrame | None = None
        self._node_types: dict[str, str] = {}
        self._node_list: list[str] = []
        self._node_to_idx: dict[str, int] = {}
        self._edge_index: torch.Tensor | None = None
        self._edge_weights: torch.Tensor | None = None

        self._load()

    # ── Loading ─────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Read the TSV edge list and build internal data structures."""
        path = Path(self._edge_list_path)
        if not path.exists():
            logger.error(f"Edge list not found: {self._edge_list_path}")
            raise FileNotFoundError(f"Edge list not found: {self._edge_list_path}")

        self._edges = pd.read_csv(
            path,
            sep="\t",
            header=None,
            names=["source", "target", "edge_type", "weight"],
            dtype={"source": str, "target": str, "edge_type": str, "weight": float},
        )

        # Build node list and index.
        all_nodes = pd.concat([self._edges["source"], self._edges["target"]])
        self._node_list = sorted(all_nodes.unique().tolist())
        self._node_to_idx = {n: i for i, n in enumerate(self._node_list)}

        # Extract node type from naming convention:
        # gene nodes: uppercase (e.g. PPARG), drug nodes: title case (e.g. Resmetirom),
        # pathway nodes: prefixed with "GO:" or "REACT:".
        for node in self._node_list:
            if node.startswith("GO:") or node.startswith("REACT:"):
                self._node_types[node] = "pathway"
            elif node[0].isupper() and node[1:].islower():
                self._node_types[node] = "drug"
            else:
                self._node_types[node] = "gene"

        # Build edge index tensor.
        src_indices = [self._node_to_idx[s] for s in self._edges["source"]]
        tgt_indices = [self._node_to_idx[t] for t in self._edges["target"]]
        self._edge_index = torch.tensor(
            [src_indices, tgt_indices], dtype=torch.long
        )

        # Edge weights.
        self._edge_weights = torch.tensor(
            self._edges["weight"].fillna(1.0).values,
            dtype=torch.float32,
        )

        logger.info(
            f"Knowledge graph loaded: {self.get_node_count()} nodes, "
            f"{self.get_edge_count()} edges from {self._edge_list_path}"
        )

    # ── Accessors ───────────────────────────────────────────────────────

    def get_node_features(self, node_type: str) -> dict[str, np.ndarray]:
        """Return feature vectors for all nodes of *node_type*.

        If no pre-computed features are available, returns a one-hot
        vector based on node index.

        Parameters
        ----------
        node_type:
            One of ``"gene"``, ``"drug"``, ``"pathway"``.

        Returns
        -------
        dict[str, np.ndarray]
            Mapping from node ID to a numpy feature vector.
        """
        n_total = len(self._node_list)
        features: dict[str, np.ndarray] = {}

        for node_id in self._node_list:
            if self._node_types.get(node_id) != node_type:
                continue
            idx = self._node_to_idx[node_id]
            vec = np.zeros(n_total, dtype=np.float32)
            vec[idx] = 1.0
            features[node_id] = vec

        return features

    def get_edge_index(self) -> torch.Tensor:
        """Return the COO-format edge index tensor ``(2, E)``."""
        if self._edge_index is None:
            raise RuntimeError("Knowledge graph has not been loaded")
        return self._edge_index

    def get_edge_weights(self) -> torch.Tensor:
        """Return the edge weight tensor ``(E,)``."""
        if self._edge_weights is None:
            raise RuntimeError("Knowledge graph has not been loaded")
        return self._edge_weights

    def get_subgraph(
        self, node_ids: list[str]
    ) -> tuple[torch.Tensor, torch.Tensor, dict[str, int]]:
        """Extract a subgraph containing only the specified nodes.

        Parameters
        ----------
        node_ids:
            List of node identifiers.

        Returns
        -------
        (edge_index, edge_weights, node_map)
            ``edge_index`` in COO format, ``edge_weights``, and
            ``node_map`` mapping original node IDs to subgraph indices.
        """
        id_set = set(node_ids)
        node_map = {n: i for i, n in enumerate(node_ids)}

        src_list: list[int] = []
        tgt_list: list[int] = []
        weight_list: list[float] = []

        for _, row in self._edges.iterrows():
            s, t = row["source"], row["target"]
            if s in id_set and t in id_set:
                src_list.append(node_map[s])
                tgt_list.append(node_map[t])
                weight_list.append(row["weight"] if pd.notna(row["weight"]) else 1.0)

        if not src_list:
            edge_index = torch.zeros((2, 0), dtype=torch.long)
            edge_weights = torch.zeros(0, dtype=torch.float32)
        else:
            edge_index = torch.tensor([src_list, tgt_list], dtype=torch.long)
            edge_weights = torch.tensor(weight_list, dtype=torch.float32)

        return edge_index, edge_weights, node_map

    def get_node_count(self) -> int:
        """Return the total number of unique nodes."""
        return len(self._node_list)

    def get_edge_count(self) -> int:
        """Return the total number of edges."""
        if self._edges is None:
            return 0
        return len(self._edges)

    def get_node_type(self, node_id: str) -> str:
        """Return the inferred type of a node (gene/drug/pathway)."""
        return self._node_types.get(node_id, "unknown")

    def get_gene_indices(self) -> list[int]:
        """Return indices of all gene nodes."""
        return [
            self._node_to_idx[n]
            for n in self._node_list
            if self._node_types.get(n) == "gene"
        ]

    def get_drug_indices(self) -> list[int]:
        """Return indices of all drug nodes."""
        return [
            self._node_to_idx[n]
            for n in self._node_list
            if self._node_types.get(n) == "drug"
        ]

    def get_gene_names(self) -> list[str]:
        """Return names of all gene nodes."""
        return [
            n for n in self._node_list if self._node_types.get(n) == "gene"
        ]

    def get_drug_names(self) -> list[str]:
        """Return names of all drug nodes."""
        return [
            n for n in self._node_list if self._node_types.get(n) == "drug"
        ]

    def get_stats(self) -> dict:
        """Return a summary of the knowledge graph."""
        gene_count = sum(
            1 for t in self._node_types.values() if t == "gene"
        )
        drug_count = sum(
            1 for t in self._node_types.values() if t == "drug"
        )
        pathway_count = sum(
            1 for t in self._node_types.values() if t == "pathway"
        )
        avg_degree = (
            (2 * self.get_edge_count() / self.get_node_count())
            if self.get_node_count() > 0
            else 0
        )

        return {
            "nodes": self.get_node_count(),
            "edges": self.get_edge_count(),
            "genes": gene_count,
            "drugs": drug_count,
            "pathways": pathway_count,
            "avg_degree": round(avg_degree, 2),
        }