"""Fetch hourly Delhi air quality and weather data from Open-Meteo,
clean it, and merge it into one tidy table.

Run from the project folder with the virtual environment active:
    python ingest.py
    python ingest.py --past-days 30
"""
import argparse
import logging

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LAT, LON = 28.6139, 77.2090  # Delhi
TZ = "Asia/Kolkata"

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"

AQ_COLUMNS = ["pm2_5", "pm10", "us_aqi"]
WX_COLUMNS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"]

# Plausible ranges. Values outside them are treated as bad data and set to null.
VALID_RANGES = {
    "pm2_5": (0, 2000),
    "pm10": (0, 3000),
    "us_aqi": (0, 1000),
    "temperature_2m": (-50, 60),
    "relative_humidity_2m": (0, 100),
    "wind_speed_10m": (0, 300),
}

log = logging.getLogger("ingest")


def make_session() -> requests.Session:
    """HTTP session that retries on temporary server errors."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_hourly(session, url, variables, past_days) -> pd.DataFrame:
    """Download hourly data for one API and return it as a DataFrame."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": ",".join(variables),
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": TZ,
    }
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if "hourly" not in payload:
        raise ValueError(f"Unexpected response from {url}: {payload}")

    df = pd.DataFrame(payload["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    log.info("Fetched %d rows from %s", len(df), url)
    return df


def drop_future_rows(df: pd.DataFrame) -> pd.DataFrame:
    """The APIs also return hours later today. Those are forecasts, not readings."""
    now_local = pd.Timestamp.now(tz=TZ).tz_localize(None)
    kept = df[df["time"] <= now_local]
    log.info("Dropped %d future rows", len(df) - len(kept))
    return kept


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates and future rows, sort by time, null out impossible values."""
    before = len(df)
    df = df.drop_duplicates(subset="time").sort_values("time")
    if len(df) < before:
        log.warning("Removed %d duplicate timestamps", before - len(df))

    df = drop_future_rows(df)

    for column, (low, high) in VALID_RANGES.items():
        if column not in df.columns:
            continue
        bad = (df[column] < low) | (df[column] > high)
        if bad.any():
            log.warning("%s: %d values outside [%s, %s] set to null", column, bad.sum(), low, high)
            df.loc[bad, column] = pd.NA

    return df.reset_index(drop=True)


def build_dataset(past_days: int = 7) -> pd.DataFrame:
    """Fetch, clean and merge both sources into one table."""
    session = make_session()

    aq = clean(fetch_hourly(session, AQ_URL, AQ_COLUMNS, past_days))
    wx = clean(fetch_hourly(session, WX_URL, WX_COLUMNS, past_days))

    merged = aq.merge(wx, on="time", how="inner")
    log.info("Rows: air quality=%d, weather=%d, merged=%d", len(aq), len(wx), len(merged))

    if merged.empty:
        raise ValueError("Merged dataset is empty. Check the API responses.")

    missing = merged.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        log.warning("Missing values remain:\n%s", missing.to_string())

    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and clean Delhi air quality + weather data")
    parser.add_argument("--past-days", type=int, default=7, help="days of history to fetch (default 7)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    df = build_dataset(past_days=args.past_days)
    print(df.head())
    print(df.tail())
    print("Shape:", df.shape)
    print("Time range:", df["time"].min(), "->", df["time"].max())


if __name__ == "__main__":
    main()
