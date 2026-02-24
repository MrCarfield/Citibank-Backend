from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class FeatureEngineer:
    df: pd.DataFrame
    target_col: str = "wti_price"

    def add_technical(self) -> "FeatureEngineer":
        p = self.df[self.target_col]
        self.df["returns_1d"] = p.pct_change()
        self.df["returns_5d"] = p.pct_change(5)
        self.df["volatility_20d"] = self.df["returns_1d"].rolling(20).std() * np.sqrt(252)
        self.df["ma_5"] = p.rolling(5).mean()
        self.df["ma_20"] = p.rolling(20).mean()
        self.df["ma_ratio"] = self.df["ma_5"] / self.df["ma_20"]
        self.df["price_momentum"] = p.pct_change(10)

        delta = p.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        self.df["rsi_14"] = 100 - (100 / (1 + rs))
        return self

    def add_macro(self) -> "FeatureEngineer":
        self.df["dxy_change_5d"] = self.df["DTWEXBGS"].pct_change(5)
        self.df["vix_change"] = self.df["VIXCLS"].pct_change()
        self.df["real_yield"] = self.df["DGS10"] - self.df["CPIAUCSL"].pct_change(12) * 100
        return self

    def add_supply(self) -> "FeatureEngineer":
        self.df["inventory_change"] = self.df["crude_inventory"].diff(7)
        self.df["inventory_deviation"] = (
            self.df["crude_inventory"] - self.df["crude_inventory"].rolling(52).mean()
        ) / self.df["crude_inventory"].rolling(52).std()
        return self

    def add_event_proxies(self) -> "FeatureEngineer":
        self.df["event_intensity"] = self.df["volatility_20d"].rolling(5).mean()
        self.df["shock_flag"] = (self.df["returns_1d"].abs() > self.df["returns_1d"].rolling(60).std() * 2).astype(int)
        self.df["gdelt_event_count_7d"] = self.df.get("gdelt_event_count", 0.0).rolling(7).sum()
        self.df["gdelt_tone_7d"] = self.df.get("gdelt_tone", 0.0).rolling(7).mean()
        self.df["calendar_intensity_7d"] = self.df.get("calendar_intensity", 0.0).rolling(7).sum()
        self.df["calendar_flag_7d"] = self.df.get("calendar_flag", 0.0).rolling(7).max()
        return self

    def add_lags(self, cols: List[str], lags: List[int]) -> "FeatureEngineer":
        for col in cols:
            for lag in lags:
                self.df[f"{col}_lag{lag}"] = self.df[col].shift(lag)
        return self

    def create_targets(self, horizon: int) -> "FeatureEngineer":
        p = self.df[self.target_col]
        future_return = p.shift(-horizon) / p - 1
        direction = (future_return > 0).astype("Int64")
        direction[future_return.isna()] = pd.NA
        self.df["target_direction"] = direction
        self.df["target_return"] = future_return

        future_vol = self.df["returns_1d"].shift(-horizon).rolling(horizon).std(ddof=0)
        future_drawdown = (
            p.shift(-horizon).rolling(horizon).max() / p.shift(-horizon).rolling(horizon).min() - 1
        )
        risk_score = future_vol * 100 + future_drawdown * 50
        risk_level = pd.cut(
            risk_score,
            bins=[-np.inf, 2, 5, np.inf],
            labels=[0, 1, 2],
        ).astype("Int64")
        risk_level[risk_score.isna()] = pd.NA
        self.df["target_risk_level"] = risk_level
        return self

    def build(self, horizon: int) -> Tuple[pd.DataFrame, pd.DataFrame, List[str], Dict[str, List[str]]]:
        self.add_technical().add_macro().add_supply().add_event_proxies().create_targets(horizon)

        feature_groups = {
            "technical": [
                "returns_1d",
                "returns_5d",
                "volatility_20d",
                "ma_ratio",
                "price_momentum",
                "rsi_14",
            ],
            "macro": ["dxy_change_5d", "vix_change", "real_yield"],
            "supply": ["inventory_change", "inventory_deviation"],
            "events": [
                "event_intensity",
                "shock_flag",
                "gdelt_event_count_7d",
                "gdelt_tone_7d",
                "calendar_intensity_7d",
                "calendar_flag_7d",
            ],
        }

        lag_cols = [c for group in feature_groups.values() for c in group]
        self.add_lags(lag_cols, [1, 3, 5])

        all_features = []
        for group in feature_groups.values():
            all_features.extend(group)
            for lag in [1, 3, 5]:
                all_features.extend([f"{c}_lag{lag}" for c in group])

        all_features = [c for c in all_features if c in self.df.columns]
        feature_df = self.df[["date"] + all_features].dropna().copy()
        target_df = self.df.loc[feature_df.index, [
            "date",
            "target_direction",
            "target_risk_level",
            "target_return",
            "wti_price",
        ]].copy()
        target_df = target_df.dropna()
        feature_df = feature_df.loc[target_df.index]
        return feature_df, target_df, all_features, feature_groups
