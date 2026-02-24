from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class FactorGate(nn.Module):
    def __init__(self, input_dim: int, num_factors: int):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(input_dim, max(8, input_dim // 2)),
            nn.ReLU(),
            nn.Linear(max(8, input_dim // 2), num_factors),
            nn.Sigmoid(),
        )

    def forward(self, x_last: torch.Tensor) -> torch.Tensor:
        return self.gate(x_last)


class MTRiskNet(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        num_factors: int,
        factor_groups: List[List[int]],
        dropout: float = 0.2,
    ):
        super().__init__()
        self.input_dim = input_dim
        self.factor_groups = factor_groups
        self.factor_gate = FactorGate(input_dim, num_factors)

        self.feature_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        self.gru = nn.GRU(hidden_dim, hidden_dim, batch_first=True)

        self.direction_head = nn.Sequential(
            nn.Linear(hidden_dim + num_factors, 64),
            nn.ReLU(),
            nn.Linear(64, 2),
        )
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim + num_factors, 64),
            nn.ReLU(),
            nn.Linear(64, 3),
        )
        self.return_head = nn.Sequential(
            nn.Linear(hidden_dim + num_factors, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def _group_features(self, x_last: torch.Tensor) -> torch.Tensor:
        groups = []
        for indices in self.factor_groups:
            if not indices:
                groups.append(torch.zeros(x_last.size(0), 1, device=x_last.device))
            else:
                groups.append(x_last[:, indices].mean(dim=1, keepdim=True))
        return torch.cat(groups, dim=1)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        x_last = x[:, -1, :]
        factor_importance = self.factor_gate(x_last)
        group_features = self._group_features(x_last) * factor_importance

        encoded = self.feature_encoder(x)
        _, h = self.gru(encoded)
        context = h[-1]

        context = torch.cat([context, group_features], dim=1)

        return {
            "direction_logits": self.direction_head(context),
            "risk_logits": self.risk_head(context),
            "return_pred": self.return_head(context).squeeze(1),
            "factor_importance": factor_importance,
        }


@dataclass
class LossOutput:
    total: torch.Tensor
    direction: torch.Tensor
    risk: torch.Tensor
    ret: torch.Tensor


def compute_loss(outputs: Dict[str, torch.Tensor], batch: Dict[str, torch.Tensor]) -> LossOutput:
    direction_loss = F.cross_entropy(outputs["direction_logits"], batch["direction"])
    risk_loss = F.cross_entropy(outputs["risk_logits"], batch["risk"])
    ret_loss = F.mse_loss(outputs["return_pred"], batch["return"])
    total = direction_loss + risk_loss + ret_loss
    return LossOutput(total=total, direction=direction_loss, risk=risk_loss, ret=ret_loss)
