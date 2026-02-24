from dataclasses import dataclass
import os


def _env_flag(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "y"}


@dataclass
class Settings:
    start_date: str = os.getenv("OIL_START_DATE", "2015-01-01")
    end_date: str = os.getenv("OIL_END_DATE", "")
    forecast_horizon: int = int(os.getenv("OIL_FORECAST_HORIZON", "5"))
    lookback: int = int(os.getenv("OIL_LOOKBACK", "20"))
    train_ratio: float = float(os.getenv("OIL_TRAIN_RATIO", "0.8"))
    batch_size: int = int(os.getenv("OIL_BATCH_SIZE", "64"))
    learning_rate: float = float(os.getenv("OIL_LR", "1e-3"))
    max_epochs: int = int(os.getenv("OIL_EPOCHS", "30"))
    random_seed: int = int(os.getenv("OIL_SEED", "42"))

    fred_api_key: str = os.getenv("FRED_API_KEY", "")
    eia_api_key: str = os.getenv("EIA_API_KEY", "")
    eia_inventory_url: str = os.getenv("EIA_INVENTORY_URL", "")
    eia_inventory_field: str = os.getenv("EIA_INVENTORY_FIELD", "value")

    gdelt_query: str = os.getenv("OIL_GDELT_QUERY", "")
    gdelt_days: int = int(os.getenv("OIL_GDELT_DAYS", "365"))
    gdelt_lang: str = os.getenv("OIL_GDELT_LANG", "")
    event_calendar_path: str = os.getenv("OIL_EVENT_CALENDAR_PATH", "oil_risk/event_calendar.json")

    use_yahoo: bool = _env_flag("OIL_USE_YAHOO", "0")

    artifacts_dir: str = os.getenv("OIL_ARTIFACTS_DIR", "../artifacts")
