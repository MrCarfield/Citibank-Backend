from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
import logging
import os

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader

from .config import Settings
from .data_sources import DataCollector
from .dataset import SequenceDataset, split_by_time
from .features import FeatureEngineer
from .model import MTRiskNet, compute_loss

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    date: str
    current_price: float
    forecast_price: float
    direction: str
    direction_prob: float
    risk_level: str
    risk_probs: Dict[str, float]
    factor_importance: Dict[str, float]


class OilRiskPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.factor_names: List[str] = []
        self.factor_groups: List[List[int]] = []
        self.model: MTRiskNet | None = None

    def _build_factor_groups(self, feature_groups: Dict[str, List[str]]) -> None:
        self.factor_names = list(feature_groups.keys())
        group_indices: List[List[int]] = []
        for name in self.factor_names:
            indices = [self.feature_names.index(f) for f in feature_groups[name] if f in self.feature_names]
            group_indices.append(indices)
        self.factor_groups = group_indices

    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
        collector = DataCollector(
            start_date=self.settings.start_date,
            end_date=self.settings.end_date or None,
            fred_api_key=self.settings.fred_api_key,
            eia_api_key=self.settings.eia_api_key,
            seed=self.settings.random_seed,
            cache_dir=self.settings.artifacts_dir,
            use_yahoo=self.settings.use_yahoo,
            eia_inventory_url=self.settings.eia_inventory_url,
            eia_inventory_field=self.settings.eia_inventory_field,
            gdelt_query=self.settings.gdelt_query,
            gdelt_days=self.settings.gdelt_days,
            gdelt_lang=self.settings.gdelt_lang,
            event_calendar_path=self.settings.event_calendar_path,
        )
        raw = collector.build_master_dataset()
        engineer = FeatureEngineer(raw)
        feature_df, target_df, feature_names, feature_groups = engineer.build(self.settings.forecast_horizon)

        self.feature_names = feature_names
        self._build_factor_groups(feature_groups)

        data = feature_df.merge(target_df, on="date")
        if data.empty:
            logger.error(
                "No training samples after feature/target merge. "
                "features=%s targets=%s horizon=%s",
                feature_df.shape,
                target_df.shape,
                self.settings.forecast_horizon,
            )
            raise ValueError("No training samples after feature/target merge")
        X = data[self.feature_names].values
        y_dir = data["target_direction"].values
        y_risk = data["target_risk_level"].values
        y_ret = data["target_return"].values

        X = self.scaler.fit_transform(X)
        return X, y_dir, y_risk, y_ret, data

    def train(self) -> None:
        torch.manual_seed(self.settings.random_seed)
        X, y_dir, y_risk, y_ret, data = self.prepare_data()

        train_idx, val_idx = split_by_time(len(X), self.settings.train_ratio)
        train_dataset = SequenceDataset(
            X[train_idx], y_dir[train_idx], y_risk[train_idx], y_ret[train_idx], self.settings.lookback
        )
        val_dataset = SequenceDataset(
            X[val_idx], y_dir[val_idx], y_risk[val_idx], y_ret[val_idx], self.settings.lookback
        )

        train_loader = DataLoader(train_dataset, batch_size=self.settings.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=self.settings.batch_size, shuffle=False)

        self.model = MTRiskNet(
            input_dim=X.shape[1],
            hidden_dim=128,
            num_factors=len(self.factor_names),
            factor_groups=self.factor_groups,
            dropout=0.2,
        )

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.settings.learning_rate)

        for epoch in range(self.settings.max_epochs):
            self.model.train()
            for batch in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch["features"])
                loss = compute_loss(outputs, batch)
                loss.total.backward()
                optimizer.step()

            self.model.eval()
            val_losses = []
            with torch.no_grad():
                for batch in val_loader:
                    outputs = self.model(batch["features"])
                    loss = compute_loss(outputs, batch)
                    val_losses.append(loss.total.item())

            _ = float(np.mean(val_losses))

        self._save_artifacts(data)

    def _save_artifacts(self, data: pd.DataFrame) -> None:
        os.makedirs(self.settings.artifacts_dir, exist_ok=True)
        model_path = os.path.join(self.settings.artifacts_dir, "mt_risknet.pt")
        scaler_path = os.path.join(self.settings.artifacts_dir, "scaler.joblib")
        meta_path = os.path.join(self.settings.artifacts_dir, "meta.json")

        torch.save(self.model.state_dict(), model_path)
        joblib.dump(self.scaler, scaler_path)

        meta = {
            "feature_names": self.feature_names,
            "factor_names": self.factor_names,
            "factor_groups": self.factor_groups,
            "forecast_horizon": self.settings.forecast_horizon,
            "lookback": self.settings.lookback,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        latest = data.tail(1)
        latest.to_csv(os.path.join(self.settings.artifacts_dir, "latest_row.csv"), index=False)

    def load(self) -> None:
        model_path = os.path.join(self.settings.artifacts_dir, "mt_risknet.pt")
        scaler_path = os.path.join(self.settings.artifacts_dir, "scaler.joblib")
        meta_path = os.path.join(self.settings.artifacts_dir, "meta.json")
        if not os.path.exists(meta_path):
            horizon_dir = os.path.join(self.settings.artifacts_dir, f"h{self.settings.forecast_horizon}")
            alt_meta = os.path.join(horizon_dir, "meta.json")
            if os.path.exists(alt_meta):
                logger.info("Switching artifacts_dir to %s", horizon_dir)
                self.settings.artifacts_dir = horizon_dir
                model_path = os.path.join(self.settings.artifacts_dir, "mt_risknet.pt")
                scaler_path = os.path.join(self.settings.artifacts_dir, "scaler.joblib")
                meta_path = alt_meta

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.feature_names = meta["feature_names"]
        self.factor_names = meta["factor_names"]
        self.factor_groups = meta["factor_groups"]

        self.scaler = joblib.load(scaler_path)
        self.model = MTRiskNet(
            input_dim=len(self.feature_names),
            hidden_dim=128,
            num_factors=len(self.factor_names),
            factor_groups=self.factor_groups,
            dropout=0.0,
        )
        self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
        self.model.eval()

    def predict_latest(self) -> PredictionResult:
        collector = DataCollector(
            start_date=self.settings.start_date,
            end_date=self.settings.end_date or None,
            fred_api_key=self.settings.fred_api_key,
            eia_api_key=self.settings.eia_api_key,
            seed=self.settings.random_seed,
            cache_dir=self.settings.artifacts_dir,
            use_yahoo=self.settings.use_yahoo,
            eia_inventory_url=self.settings.eia_inventory_url,
            eia_inventory_field=self.settings.eia_inventory_field,
            gdelt_query=self.settings.gdelt_query,
            gdelt_days=self.settings.gdelt_days,
            gdelt_lang=self.settings.gdelt_lang,
            event_calendar_path=self.settings.event_calendar_path,
        )
        raw = collector.build_master_dataset()
        engineer = FeatureEngineer(raw)
        feature_df, target_df, _, _ = engineer.build(self.settings.forecast_horizon)

        latest = feature_df.tail(self.settings.lookback)
        if latest.empty or len(latest) < self.settings.lookback:
            raise ValueError("Not enough data for lookback window")

        current_price = float(raw["wti_price"].iloc[-1])
        latest_scaled = self.scaler.transform(latest[self.feature_names].values)
        x = torch.tensor(latest_scaled, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            outputs = self.model(x)
            direction_prob = torch.softmax(outputs["direction_logits"], dim=1)[0, 1].item()
            risk_probs = torch.softmax(outputs["risk_logits"], dim=1)[0].tolist()
            pred_return = outputs["return_pred"][0].item()
            factor_importance = outputs["factor_importance"][0].tolist()

        forecast_price = current_price * (1 + pred_return)
        direction = "up" if direction_prob >= 0.5 else "down"
        risk_labels = ["low", "medium", "high"]
        risk_level = risk_labels[int(np.argmax(risk_probs))]

        return PredictionResult(
            date=raw["date"].iloc[-1].strftime("%Y-%m-%d"),
            current_price=current_price,
            forecast_price=forecast_price,
            direction=direction,
            direction_prob=direction_prob,
            risk_level=risk_level,
            risk_probs={k: float(v) for k, v in zip(risk_labels, risk_probs)},
            factor_importance={
                name: float(val) for name, val in zip(self.factor_names, factor_importance)
            },
        )
