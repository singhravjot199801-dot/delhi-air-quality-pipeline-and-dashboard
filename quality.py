"""Data quality checks for the merged Delhi air quality + weather dataset.

run_checks() returns two lists: errors (the data should NOT be loaded)
and warnings (worth knowing about, but the load can continue).
"""
import pandas as pd

from ingest import AQ_COLUMNS, TZ, VALID_RANGES, WX_COLUMNS

VALUE_COLUMNS = AQ_COLUMNS + WX_COLUMNS
REQUIRED_COLUMNS = ["time"] + VALUE_COLUMNS

MAX_NULL_FRACTION = 0.10   # more than 10% missing in a column is an error
MAX_STALENESS_HOURS = 6    # newest row older than this means the source is stale
EXPECTED_STEP = pd.Timedelta(hours=1)


def run_checks(df: pd.DataFrame, now: pd.Timestamp | None = None):
    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        return ["dataset is empty"], warnings

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        return [f"missing columns: {missing_cols}"], warnings

    # Timestamps: unique and in order
    duplicates = int(df["time"].duplicated().sum())
    if duplicates:
        errors.append(f"{duplicates} duplicate timestamps")
    if not df["time"].is_monotonic_increasing:
        errors.append("timestamps are not sorted")

    # Gaps: the data should be hourly
    gaps = df["time"].diff().dropna()
    big_gaps = gaps[gaps > EXPECTED_STEP]
    if not big_gaps.empty:
        warnings.append(f"{len(big_gaps)} gaps longer than 1 hour (largest: {big_gaps.max()})")

    # Per-column checks: missing values and plausible ranges
    for column in VALUE_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")

        null_fraction = float(values.isna().mean())
        if null_fraction > MAX_NULL_FRACTION:
            errors.append(f"{column}: {null_fraction:.0%} null values")
        elif null_fraction > 0:
            warnings.append(f"{column}: {null_fraction:.0%} null values")

        low, high = VALID_RANGES[column]
        out_of_range = int(((values < low) | (values > high)).sum())
        if out_of_range:
            errors.append(f"{column}: {out_of_range} values outside [{low}, {high}]")

    # Freshness: is the newest row recent?
    if now is None:
        now = pd.Timestamp.now(tz=TZ).tz_localize(None)
    age = now - df["time"].max()
    if age > pd.Timedelta(hours=MAX_STALENESS_HOURS):
        errors.append(f"data is stale: newest row is {age} old")

    return errors, warnings
