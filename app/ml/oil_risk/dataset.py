from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset


class SequenceDataset(Dataset):
    def __init__(self, X: np.ndarray, y_dir: np.ndarray, y_risk: np.ndarray, y_ret: np.ndarray, lookback: int):
        self.X = X
        self.y_dir = y_dir
        self.y_risk = y_risk
        self.y_ret = y_ret
        self.lookback = lookback

    def __len__(self) -> int:
        return len(self.X) - self.lookback

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        x_seq = self.X[idx : idx + self.lookback]
        y_idx = idx + self.lookback - 1
        return {
            "features": torch.tensor(x_seq, dtype=torch.float32),
            "direction": torch.tensor(self.y_dir[y_idx], dtype=torch.long),
            "risk": torch.tensor(self.y_risk[y_idx], dtype=torch.long),
            "return": torch.tensor(self.y_ret[y_idx], dtype=torch.float32),
        }


def split_by_time(n: int, train_ratio: float) -> Tuple[np.ndarray, np.ndarray]:
    split = int(n * train_ratio)
    train_idx = np.arange(0, split)
    val_idx = np.arange(split, n)
    return train_idx, val_idx
