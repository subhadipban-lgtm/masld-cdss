"""Two-layer mean-aggregation GraphSAGE model for MASLD drug ranking.

Architecture mirrors the model described in the MASLD DrugScope
publication: two ``SAGEConv`` layers with mean aggregation, followed
by a ReLU activation between layers.  Weights can be loaded from a
pre-trained ``.pt`` checkpoint; if unavailable the model is
initialised randomly with a logged warning.
"""

from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from app.core.logging import get_logger

logger = get_logger(__name__)


class GraphSAGE(nn.Module):
    """Two-layer GraphSAGE with mean aggregation.

    Parameters
    ----------
    in_dim:
        Dimensionality of input node features.
    hidden_dim:
        Dimensionality of the first SAGEConv output (and second-layer input).
    out_dim:
        Dimensionality of the final embedding space.
    """

    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int) -> None:
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden_dim, aggr="mean")
        self.conv2 = SAGEConv(hidden_dim, out_dim, aggr="mean")

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """Run a forward pass through the two GraphSAGE layers.

        Parameters
        ----------
        x:
            Node feature matrix of shape ``(num_nodes, in_dim)``.
        edge_index:
            Edge indices of shape ``(2, num_edges)`` in COO format.

        Returns
        -------
        torch.Tensor
            Node embeddings of shape ``(num_nodes, out_dim)``.
        """
        h = self.conv1(x, edge_index)
        h = F.relu(h)
        h = F.dropout(h, p=0.1, training=self.training)
        h = self.conv2(h, edge_index)
        return h


# ── SAGEConv (standalone, no torch_geometric dependency at import time) ──

class SAGEConv(nn.Module):
    """GraphSAGE convolution layer with mean aggregation.

    Implements the neighbourhood aggregation step:
    ``h_v = σ(W · MEAN({h_u : u ∈ N(v)}) || h_v)``
    """

    def __init__(self, in_channels: int, out_channels: int, aggr: str = "mean") -> None:
        super().__init__()
        self.aggr = aggr
        self.linear = nn.Linear(in_channels * 2, out_channels, bias=True)
        self.act = nn.LeakyReLU(0.2)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.linear.weight)
        if self.linear.bias is not None:
            nn.init.zeros_(self.linear.bias)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
    ) -> torch.Tensor:
        """Aggregate neighbour features and combine with self-features.

        Parameters
        ----------
        x:
            Node features ``(N, in_channels)``.
        edge_index:
            COO edge tensor ``(2, E)``.

        Returns
        -------
        torch.Tensor
            Updated node features ``(N, out_channels)``.
        """
        num_nodes = x.size(0)
        row, col = edge_index[0], edge_index[1]

        # Aggregate neighbour features.
        # For each target node (col), mean-pool the source nodes (row).
        neighbour_sum = torch.zeros_like(x)
        neighbour_count = torch.zeros(num_nodes, 1, device=x.device)

        ones = torch.ones(row.size(0), 1, device=x.device)
        neighbour_sum.scatter_add_(0, col.unsqueeze(1).expand_as(x), x)
        neighbour_count.scatter_add_(0, col.unsqueeze(1), ones)

        # Avoid division by zero for isolated nodes.
        neighbour_count = neighbour_count.clamp(min=1)
        neighbour_mean = neighbour_sum / neighbour_count

        # Concatenate self-features and neighbour features.
        combined = torch.cat([x, neighbour_mean], dim=-1)
        out = self.linear(combined)
        return self.act(out)


# ── Weight Loading ──────────────────────────────────────────────────────


def load_pretrained_weights(model: GraphSAGE, weights_path: str) -> None:
    """Load frozen weights from a ``.pt`` checkpoint into *model*.

    After loading, all parameters are set to ``requires_grad=False``
    so the model is used purely for inference.

    If the weights file does not exist, the model is left with its
    random initialisation and a warning is logged.

    Parameters
    ----------
    model:
        A ``GraphSAGE`` instance.
    weights_path:
        Path to the ``.pt`` file containing a ``state_dict``.
    """
    path = Path(weights_path)
    if not path.exists():
        logger.warning(
            f"Model weights not found at {weights_path}. "
            f"Using random initialisation — predictions will not be "
            f"scientifically valid."
        )
        return

    try:
        state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state_dict, strict=False)
        # Freeze all parameters for inference.
        for param in model.parameters():
            param.requires_grad = False
        model.eval()
        logger.info(f"Loaded and froze pretrained weights from {weights_path}")
    except Exception as exc:
        logger.warning(
            f"Failed to load model weights from {weights_path}: {exc}. "
            f"Falling back to random initialisation."
        )