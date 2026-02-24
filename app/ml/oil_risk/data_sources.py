from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json
import io
import logging
import os
import time
import urllib.parse

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


@dataclass
class DataCollector:
    start_date: str
    end_date: Optional[str] = None
    fred_api_key: str = ""
    eia_api_key: str = ""
    seed: int = 42
    cache_dir: str = "../artifacts"
    use_yahoo: bool = False
    eia_inventory_url: str = ""
    eia_inventory_field: str = "value"
    gdelt_query: str = ""
    gdelt_days: int = 365
    gdelt_lang: str = ""
    event_calendar_path: str = "oil_risk/event_calendar.json"

    def _cache_path(self, ticker: str) -> str:
        safe = ticker.replace("=", "_").replace("/", "_")
        return os.path.join(self.cache_dir, "market_cache", f"{safe}.csv")

    def _load_cached_yahoo(self, ticker: str, col_name: str) -> pd.DataFrame:
        path = self._cache_path(ticker)
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            df = pd.read_csv(path)
            if "date" not in df.columns or col_name not in df.columns:
                return pd.DataFrame()
            df["date"] = pd.to_datetime(df["date"])
            if f"{col_name}_volume" not in df.columns:
                df[f"{col_name}_volume"] = 0.0
            start = pd.to_datetime(self.start_date)
            if self.end_date:
                end = pd.to_datetime(self.end_date)
                df = df[(df["date"] >= start) & (df["date"] <= end)]
            else:
                df = df[df["date"] >= start]
            return df[["date", col_name, f"{col_name}_volume"]]
        except Exception:
            return pd.DataFrame()

    def _save_cached_yahoo(self, ticker: str, df: pd.DataFrame) -> None:
        path = self._cache_path(ticker)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)

    def _date_range(self) -> pd.DatetimeIndex:
        end = self.end_date or datetime.now().strftime("%Y-%m-%d")
        return pd.date_range(self.start_date, end, freq="D")

    def fetch_fred_series(self, series_id: str) -> pd.DataFrame:
        end_date = self.end_date or datetime.now().strftime("%Y-%m-%d")

        def fetch_csv() -> pd.DataFrame:
            url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
            params = {
                "id": series_id,
                "cosd": self.start_date,
                "coed": end_date,
            }
            try:
                response = requests.get(url, params=params, timeout=20)
                response.raise_for_status()
                df = pd.read_csv(io.StringIO(response.text))
                df.columns = [str(col).strip() for col in df.columns]
                date_col = None
                if "DATE" in df.columns:
                    date_col = "DATE"
                elif "observation_date" in df.columns:
                    date_col = "observation_date"
                if not date_col:
                    logger.debug("FRED CSV missing date column for %s. Columns=%s", series_id, df.columns)
                    return pd.DataFrame()
                if series_id not in df.columns:
                    matches = [c for c in df.columns if c.replace(" ", "") == series_id]
                    if matches:
                        df = df.rename(columns={matches[0]: series_id})
                    else:
                        logger.debug("FRED CSV missing %s column. Columns=%s", series_id, df.columns)
                        return pd.DataFrame()
                df = df.rename(columns={date_col: "date"})
                df["date"] = pd.to_datetime(df["date"])
                df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
                if df[series_id].dropna().empty:
                    logger.debug("FRED CSV %s has no valid values.", series_id)
                    return pd.DataFrame()
                return df[["date", series_id]]
            except Exception:
                return pd.DataFrame()

        if not self.fred_api_key:
            return fetch_csv()

        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "observation_start": self.start_date,
            "observation_end": end_date,
        }
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()["observations"]
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            df[series_id] = pd.to_numeric(df["value"], errors="coerce")
            if df.empty or df[series_id].dropna().empty:
                logger.debug("FRED API %s has no valid values; falling back to CSV.", series_id)
                return fetch_csv()
            return df[["date", series_id]]
        except Exception:
            return fetch_csv()

    def fetch_eia_series(self, series_id: str) -> pd.DataFrame:
        if not self.eia_api_key:
            logger.debug("EIA API key missing; skipping %s", series_id)
            return pd.DataFrame()
        end_date = self.end_date or datetime.now().strftime("%Y-%m-%d")

        def fetch_petroleum_wkly() -> pd.DataFrame:
            url = "https://api.eia.gov/v2/petroleum/stoc/wkly/data/"
            params = {
                "api_key": self.eia_api_key,
                "data[]": "value",
                "facets[series_id][]": series_id,
                "start": self.start_date,
                "end": end_date,
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
            }
            try:
                response = requests.get(url, params=params, timeout=20)
                response.raise_for_status()
                payload = response.json()
                if "response" not in payload or "data" not in payload["response"]:
                    logger.debug("EIA petroleum response missing data for %s: %s", series_id, payload)
                    return pd.DataFrame()
                data = payload["response"]["data"]
                df = pd.DataFrame(data)
                if df.empty:
                    logger.debug("EIA petroleum returned empty data for %s", series_id)
                    return pd.DataFrame()
                if "period" not in df.columns or "value" not in df.columns:
                    logger.debug("EIA petroleum columns missing for %s. Columns=%s", series_id, df.columns)
                    return pd.DataFrame()
                df["date"] = pd.to_datetime(df["period"], errors="coerce")
                df[series_id] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["date", series_id])
                if df.empty:
                    logger.debug("EIA petroleum %s has no valid values", series_id)
                    return pd.DataFrame()
                return df[["date", series_id]]
            except Exception:
                logger.exception("EIA petroleum request failed for %s", series_id)
                return pd.DataFrame()
        def fetch_v1() -> pd.DataFrame:
            url = "https://api.eia.gov/series/"
            params = {
                "api_key": self.eia_api_key,
                "series_id": series_id,
            }
            try:
                response = requests.get(url, params=params, timeout=20)
                response.raise_for_status()
                payload = response.json()
                if "series" not in payload or not payload["series"]:
                    logger.debug("EIA v1 response missing series for %s: %s", series_id, payload)
                    return pd.DataFrame()
                data = payload["series"][0].get("data", [])
                df = pd.DataFrame(data, columns=["period", "value"])
                if df.empty:
                    logger.debug("EIA v1 returned empty data for %s", series_id)
                    return pd.DataFrame()
                df["date"] = pd.to_datetime(df["period"], errors="coerce")
                df[series_id] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["date", series_id])
                if df.empty:
                    logger.debug("EIA v1 %s has no valid values", series_id)
                    return pd.DataFrame()
                return df[["date", series_id]]
            except Exception:
                logger.exception("EIA v1 request failed for %s", series_id)
                return pd.DataFrame()

        url = f"https://api.eia.gov/v2/seriesid/{series_id}/data"
        params = {
            "api_key": self.eia_api_key,
            "start": self.start_date,
            "end": end_date,
        }
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if "response" not in payload or "data" not in payload["response"]:
                logger.debug("EIA response missing data for %s: %s", series_id, payload)
                df = fetch_v1()
                if df.empty and series_id.startswith("PET."):
                    return fetch_petroleum_wkly()
                return df
            data = payload["response"]["data"]
            df = pd.DataFrame(data)
            if df.empty:
                logger.debug("EIA returned empty data for %s", series_id)
                df = fetch_v1()
                if df.empty and series_id.startswith("PET."):
                    return fetch_petroleum_wkly()
                return df
            if "period" not in df.columns or "value" not in df.columns:
                logger.debug("EIA columns missing for %s. Columns=%s", series_id, df.columns)
                df = fetch_v1()
                if df.empty and series_id.startswith("PET."):
                    return fetch_petroleum_wkly()
                return df
            df["date"] = pd.to_datetime(df["period"])
            df[series_id] = pd.to_numeric(df["value"], errors="coerce")
            if df[series_id].dropna().empty:
                logger.debug("EIA %s has no valid values", series_id)
                df = fetch_v1()
                if df.empty and series_id.startswith("PET."):
                    return fetch_petroleum_wkly()
                return df
            return df[["date", series_id]]
        except Exception:
            logger.exception("EIA request failed for %s", series_id)
            df = fetch_v1()
            if df.empty and series_id.startswith("PET."):
                return fetch_petroleum_wkly()
            return df

    def fetch_eia_custom_inventory(self) -> pd.DataFrame:
        if not self.eia_inventory_url:
            return pd.DataFrame()
        if not self.eia_api_key:
            logger.debug("EIA API key missing; skipping custom inventory URL")
            return pd.DataFrame()

        url = self.eia_inventory_url
        if "{api_key}" in url:
            url = url.replace("{api_key}", self.eia_api_key)
        else:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            if "api_key" not in query:
                query["api_key"] = [self.eia_api_key]
            url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if "response" not in payload or "data" not in payload["response"]:
                logger.debug("EIA custom response missing data: %s", payload)
                return pd.DataFrame()
            df = pd.DataFrame(payload["response"]["data"])
            if df.empty:
                logger.debug("EIA custom returned empty data")
                return pd.DataFrame()
            date_col = "period" if "period" in df.columns else "date" if "date" in df.columns else None
            if not date_col:
                logger.debug("EIA custom missing date column. Columns=%s", df.columns)
                return pd.DataFrame()
            value_col = self.eia_inventory_field if self.eia_inventory_field in df.columns else None
            if not value_col and "value" in df.columns:
                value_col = "value"
            if not value_col:
                logger.debug("EIA custom missing value column. Columns=%s", df.columns)
                return pd.DataFrame()
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            df["crude_inventory"] = pd.to_numeric(df[value_col], errors="coerce")
            df = df.dropna(subset=["date", "crude_inventory"])
            if df.duplicated(subset=["date"]).any():
                df = df.groupby("date", as_index=False)["crude_inventory"].sum()
            if df.empty:
                logger.debug("EIA custom has no valid values")
                return pd.DataFrame()
            return df[["date", "crude_inventory"]]
        except Exception:
            logger.exception("EIA custom inventory request failed")
            return pd.DataFrame()

    def fetch_gdelt_events(self) -> pd.DataFrame:
        if not self.gdelt_query:
            return pd.DataFrame()

        end_date = pd.to_datetime(self.end_date or datetime.now().strftime("%Y-%m-%d"))
        start_date = pd.to_datetime(self.start_date)
        if self.gdelt_days > 0:
            start_date = max(start_date, end_date - pd.Timedelta(days=self.gdelt_days))

        def _fmt(dt: pd.Timestamp) -> str:
            return dt.strftime("%Y%m%d%H%M%S")

        all_events = []
        window_start = start_date
        while window_start <= end_date:
            window_end = min(window_start + pd.Timedelta(days=6), end_date)
            params = {
                "query": self.gdelt_query,
                "format": "json",
                "maxrecords": 250,
                "startdatetime": _fmt(window_start),
                "enddatetime": _fmt(window_end + pd.Timedelta(hours=23, minutes=59, seconds=59)),
            }
            if self.gdelt_lang:
                params["sourcelang"] = self.gdelt_lang
            try:
                response = requests.get(
                    "https://api.gdeltproject.org/api/v2/events/search",
                    params=params,
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                for event in payload.get("events", []):
                    dt_str = event.get("datetime") or ""
                    tone = event.get("tone")
                    if not dt_str:
                        continue
                    dt = pd.to_datetime(dt_str, errors="coerce")
                    if pd.isna(dt):
                        continue
                    all_events.append({"date": dt.date(), "tone": tone})
            except Exception:
                logger.exception("GDELT request failed for %s to %s", window_start, window_end)
            window_start = window_end + pd.Timedelta(days=1)

        if not all_events:
            return pd.DataFrame()

        df = pd.DataFrame(all_events)
        df["date"] = pd.to_datetime(df["date"])
        df["tone"] = pd.to_numeric(df["tone"], errors="coerce")
        agg = df.groupby("date", as_index=False).agg(
            gdelt_event_count=("tone", "count"),
            gdelt_tone=("tone", "mean"),
        )
        return agg

    def load_event_calendar(self) -> pd.DataFrame:
        if not self.event_calendar_path:
            return pd.DataFrame()
        if not os.path.exists(self.event_calendar_path):
            logger.debug("Event calendar not found: %s", self.event_calendar_path)
            return pd.DataFrame()
        try:
            if self.event_calendar_path.lower().endswith(".csv"):
                df = pd.read_csv(self.event_calendar_path)
                df = df.rename(columns={"Date": "date", "DATE": "date"})
                if "date" not in df.columns:
                    return pd.DataFrame()
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df["calendar_intensity"] = pd.to_numeric(df.get("intensity", 1), errors="coerce").fillna(1.0)
                df = df.dropna(subset=["date"])
                if df.empty:
                    return pd.DataFrame()
                agg = df.groupby("date", as_index=False).agg(
                    calendar_intensity=("calendar_intensity", "sum"),
                    calendar_event_count=("calendar_intensity", "count"),
                )
                agg["calendar_flag"] = 1
                return agg
            with open(self.event_calendar_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            logger.exception("Failed to read event calendar: %s", self.event_calendar_path)
            return pd.DataFrame()

        events = payload.get("events", payload) if isinstance(payload, dict) else payload
        if not isinstance(events, list) or not events:
            return pd.DataFrame()

        df = pd.DataFrame(events)
        if "date" not in df.columns:
            return pd.DataFrame()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["calendar_intensity"] = pd.to_numeric(df.get("intensity", 1), errors="coerce").fillna(1.0)
        df = df.dropna(subset=["date"])
        if df.empty:
            return pd.DataFrame()
        agg = df.groupby("date", as_index=False).agg(
            calendar_intensity=("calendar_intensity", "sum"),
            calendar_event_count=("calendar_intensity", "count"),
        )
        agg["calendar_flag"] = 1
        return agg
        if not self.eia_api_key:
            logger.debug("EIA API key missing; skipping custom inventory URL")
            return pd.DataFrame()

        url = self.eia_inventory_url
        if "{api_key}" in url:
            url = url.replace("{api_key}", self.eia_api_key)
        else:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            if "api_key" not in query:
                query["api_key"] = [self.eia_api_key]
            url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query, doseq=True)))

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if "response" not in payload or "data" not in payload["response"]:
                logger.debug("EIA custom response missing data: %s", payload)
                return pd.DataFrame()
            df = pd.DataFrame(payload["response"]["data"])
            if df.empty:
                logger.debug("EIA custom returned empty data")
                return pd.DataFrame()
            date_col = "period" if "period" in df.columns else "date" if "date" in df.columns else None
            if not date_col:
                logger.debug("EIA custom missing date column. Columns=%s", df.columns)
                return pd.DataFrame()
            value_col = self.eia_inventory_field if self.eia_inventory_field in df.columns else None
            if not value_col and "value" in df.columns:
                value_col = "value"
            if not value_col:
                logger.debug("EIA custom missing value column. Columns=%s", df.columns)
                return pd.DataFrame()
            df["date"] = pd.to_datetime(df[date_col], errors="coerce")
            df["crude_inventory"] = pd.to_numeric(df[value_col], errors="coerce")
            df = df.dropna(subset=["date", "crude_inventory"])
            if df.duplicated(subset=["date"]).any():
                df = df.groupby("date", as_index=False)["crude_inventory"].sum()
            if df.empty:
                logger.debug("EIA custom has no valid values")
                return pd.DataFrame()
            return df[["date", "crude_inventory"]]
        except Exception:
            logger.exception("EIA custom inventory request failed")
            return pd.DataFrame()

    def fetch_yahoo_price(self, ticker: str, col_name: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except Exception:
            return self._load_cached_yahoo(ticker, col_name)

        cached = self._load_cached_yahoo(ticker, col_name)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = yf.download(
                    ticker,
                    start=self.start_date,
                    end=self.end_date or datetime.now().strftime("%Y-%m-%d"),
                    progress=False,
                )
                if df.empty:
                    break
                df = df.reset_index()[["Date", "Close", "Volume"]]
                df.columns = ["date", col_name, f"{col_name}_volume"]
                self._save_cached_yahoo(ticker, df)
                return df
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    break

        return cached

    def _simulate_series(self, name: str, dates: pd.DatetimeIndex, base: float, scale: float) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        values = base + np.cumsum(rng.normal(0, scale, len(dates)))
        return pd.DataFrame({"date": dates, name: values})

    def _ensure_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        daily = df.set_index("date").asfreq("D")
        daily = daily.interpolate(method="time").ffill().bfill().reset_index()
        return daily

    def build_master_dataset(self) -> pd.DataFrame:
        dates = self._date_range()

        wti_source = "fred"
        wti = self.fetch_fred_series("DCOILWTICO")
        if not wti.empty:
            wti = wti.rename(columns={"DCOILWTICO": "wti_price"})
            wti["wti_price_volume"] = 0.0
        elif self.use_yahoo:
            wti_source = "yahoo"
            wti = self.fetch_yahoo_price("CL=F", "wti_price")
        else:
            wti_source = "simulated"

        brent_source = "fred"
        brent = self.fetch_fred_series("DCOILBRENTEU")
        if not brent.empty:
            brent = brent.rename(columns={"DCOILBRENTEU": "brent_price"})
        elif self.use_yahoo:
            brent_source = "yahoo"
            brent = self.fetch_yahoo_price("BZ=F", "brent_price")
        else:
            brent_source = "simulated"

        if wti.empty:
            wti_source = "simulated"
            wti = self._simulate_series("wti_price", dates, base=70.0, scale=0.3)
            wti["wti_price_volume"] = 0.0
        if brent.empty:
            brent_source = "simulated"
            brent = self._simulate_series("brent_price", dates, base=72.0, scale=0.3)

        logger.info("Price source: WTI=%s, Brent=%s", wti_source, brent_source)

        wti = self._ensure_daily(wti)
        brent = self._ensure_daily(brent)

        master = pd.merge(wti, brent, on="date", how="outer")
        master["wti_brent_spread"] = master["brent_price"] - master["wti_price"]

        dxy = self.fetch_fred_series("DTWEXBGS")
        vix = self.fetch_fred_series("VIXCLS")
        dgs10 = self.fetch_fred_series("DGS10")
        cpi = self.fetch_fred_series("CPIAUCSL")

        macro_fallbacks = []
        if dxy.empty:
            macro_fallbacks.append("DTWEXBGS")
            dxy = self._simulate_series("DTWEXBGS", dates, base=100.0, scale=0.05)
        if vix.empty:
            macro_fallbacks.append("VIXCLS")
            vix = self._simulate_series("VIXCLS", dates, base=20.0, scale=0.2)
        if dgs10.empty:
            macro_fallbacks.append("DGS10")
            dgs10 = self._simulate_series("DGS10", dates, base=2.0, scale=0.01)
        if cpi.empty:
            macro_fallbacks.append("CPIAUCSL")
            cpi = self._simulate_series("CPIAUCSL", dates, base=260.0, scale=0.05)

        if macro_fallbacks:
            logger.info("Macro fallback simulated: %s", ", ".join(macro_fallbacks))

        for macro in [dxy, vix, dgs10, cpi]:
            macro = self._ensure_daily(macro)
            master = pd.merge(master, macro, on="date", how="left")

        inventory = pd.DataFrame()
        inventory_source = "eia"
        if self.eia_inventory_url:
            inventory = self.fetch_eia_custom_inventory()
            if not inventory.empty:
                inventory_source = "eia_custom"

        if inventory.empty:
            inventory = self.fetch_eia_series("PET.WCESTUS1.W")
            if inventory.empty:
                inventory_source = "simulated"
                weekly = pd.date_range(dates.min(), dates.max(), freq="W")
                inventory = self._simulate_series("crude_inventory", weekly, base=420.0, scale=1.2)
            else:
                inventory = inventory.rename(columns={"PET.WCESTUS1.W": "crude_inventory"})

        logger.info("Inventory source: %s", inventory_source)

        inventory = self._ensure_daily(inventory)
        master = pd.merge(master, inventory, on="date", how="left")

        gdelt = self.fetch_gdelt_events()
        if gdelt.empty:
            gdelt = pd.DataFrame({
                "date": dates,
                "gdelt_event_count": 0.0,
                "gdelt_tone": 0.0,
            })
        master = pd.merge(master, gdelt, on="date", how="left")

        calendar = self.load_event_calendar()
        if calendar.empty:
            calendar = pd.DataFrame({
                "date": dates,
                "calendar_intensity": 0.0,
                "calendar_event_count": 0.0,
                "calendar_flag": 0.0,
            })
        master = pd.merge(master, calendar, on="date", how="left")

        for col in [
            "gdelt_event_count",
            "gdelt_tone",
            "calendar_intensity",
            "calendar_event_count",
            "calendar_flag",
        ]:
            if col in master.columns:
                master[col] = master[col].fillna(0.0)

        master = master.sort_values("date").ffill().bfill()
        return master
