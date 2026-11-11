"""Load the cleaned Delhi air quality + weather data into Postgres.

The load is idempotent: running it twice does not create duplicate rows,
because each hour is keyed on its timestamp and existing rows are updated.

Setup:
    1. Put your connection string in a .env file:  DATABASE_URL=postgresql://...
    2. pip install psycopg2-binary python-dotenv

Run from the project folder with the virtual environment active:
    python load.py
    python load.py --past-days 30
"""

import argparse
import logging
import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from ingest import build_dataset
from quality import run_checks

TABLE = "delhi_air_weather"

COLUMNS = [
    "time",
    "pm2_5",
    "pm10",
    "us_aqi",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
]

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    time                  TIMESTAMP PRIMARY KEY,
    pm2_5                 DOUBLE PRECISION,
    pm10                  DOUBLE PRECISION,
    us_aqi                DOUBLE PRECISION,
    temperature_2m        DOUBLE PRECISION,
    relative_humidity_2m  DOUBLE PRECISION,
    wind_speed_10m        DOUBLE PRECISION,
    ingested_at           TIMESTAMPTZ DEFAULT now()
);
"""

_updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLUMNS if c != "time")
UPSERT_SQL = (
    f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}) VALUES %s "
    f"ON CONFLICT (time) DO UPDATE SET {_updates}, ingested_at = now()"
)

log = logging.getLogger("load")


def get_connection():
    load_dotenv()  # reads DATABASE_URL from a local .env file if present
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to a .env file or set it as an environment variable."
        )
    return psycopg2.connect(url)


def to_rows(df):
    """Turn the DataFrame into a list of tuples, with NaN replaced by None (SQL NULL)."""
    subset = df[COLUMNS]
    subset = subset.astype(object).where(subset.notna(), None)
    return list(subset.itertuples(index=False, name=None))


def load(df) -> int:
    rows = to_rows(df)
    conn = get_connection()
    try:
        # "with conn" wraps everything in one transaction: all rows load, or none do
        with conn, conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
            execute_values(cur, UPSERT_SQL, rows)
            cur.execute(f"SELECT count(*), min(time), max(time) FROM {TABLE}")
            total, first, last = cur.fetchone()
    finally:
        conn.close()

    log.info("Upserted %d rows. Table now has %d rows from %s to %s", len(rows), total, first, last)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Delhi data and load it into Postgres")
    parser.add_argument("--past-days", type=int, default=7, help="days of history to fetch (default 7)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    df = build_dataset(past_days=args.past_days)

    errors, warnings = run_checks(df)
    for message in warnings:
        log.warning("Quality warning: %s", message)
    if errors:
        for message in errors:
            log.error("Quality check failed: %s", message)
        raise SystemExit("Aborting load: data quality checks failed")

    load(df)


if __name__ == "__main__":
    main()
