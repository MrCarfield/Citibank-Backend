import os
from typing import Dict

from app.schemas.translator import TranslatorRequest


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts", "oil_risk")


def _resolve_artifacts_dir() -> str:
    env_dir = os.getenv("OIL_ARTIFACTS_DIR")
    if env_dir:
        return env_dir
    return DEFAULT_ARTIFACTS_DIR


def _resolve_horizon_days(horizon_value: str) -> int:
    if horizon_value == "1w":
        return 5
    if horizon_value == "1m":
        return 10
    if horizon_value == "1q":
        return 10
    return 5


def _load_pipeline(horizon_days: int):
    from app.ml.oil_risk.config import Settings as OilSettings
    from app.ml.oil_risk.pipeline import OilRiskPipeline

    settings = OilSettings(
        forecast_horizon=horizon_days,
        artifacts_dir=_resolve_artifacts_dir(),
    )
    pipeline = OilRiskPipeline(settings)
    pipeline.load()
    return pipeline


def _predict_sync(request: TranslatorRequest) -> Dict[str, float]:
    horizon_days = _resolve_horizon_days(request.horizon.value)
    pipeline = _load_pipeline(horizon_days)
    result = pipeline.predict_latest()

    current_price = result.current_price or 0.0
    if current_price:
        ratio = result.forecast_price / current_price
    else:
        ratio = 1.0
    price_change_pct = ratio - 1.0

    risk_probs = result.risk_probs
    risk_weights = {"low": 0.08, "medium": 0.15, "high": 0.25}
    volatility_change = 0.0
    for level, prob in risk_probs.items():
        weight = risk_weights.get(level, 0.1)
        volatility_change += weight * prob

    if result.direction == "up":
        confidence_score = result.direction_prob
    else:
        confidence_score = 1.0 - result.direction_prob

    factors = sorted(result.factor_importance.items(), key=lambda x: x[1], reverse=True)
    primary_driver = factors[0][0] if factors else "unknown"
    secondary_driver = factors[1][0] if len(factors) > 1 else primary_driver

    return {
        "predicted_price_change_pct": float(price_change_pct),
        "predicted_volatility_change_pct": float(volatility_change),
        "confidence_score": float(confidence_score),
        "primary_driver": primary_driver,
        "secondary_driver": secondary_driver,
    }


async def get_oil_neural_features(request: TranslatorRequest) -> Dict[str, float]:
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _predict_sync, request)
