import pandas as pd

from ingest import AQ_COLUMNS, WX_COLUMNS
from quality import run_checks

NOW = pd.Timestamp("2026-11-11 12:00")


def make_df(hours=24):
    """A clean, valid hourly dataset ending one hour before NOW."""
    times = pd.date_range(end="2026-11-11 11:00", periods=hours, freq="h")
    df = pd.DataFrame({"time": times})
    for column in AQ_COLUMNS + WX_COLUMNS:
        df[column] = 50.0
    return df


def has(messages, text):
    return any(text in m for m in messages)


def test_clean_data_passes():
    errors, warnings = run_checks(make_df(), now=NOW)
    assert errors == []
    assert warnings == []


def test_empty_dataset_is_an_error():
    errors, _ = run_checks(make_df().iloc[0:0], now=NOW)
    assert has(errors, "empty")


def test_missing_column_is_an_error():
    df = make_df().drop(columns=["pm2_5"])
    errors, _ = run_checks(df, now=NOW)
    assert has(errors, "missing columns")


def test_duplicate_timestamps_are_an_error():
    df = pd.concat([make_df(), make_df().iloc[[0]]], ignore_index=True)
    errors, _ = run_checks(df, now=NOW)
    assert has(errors, "duplicate")


def test_out_of_range_value_is_an_error():
    df = make_df()
    df.loc[3, "pm2_5"] = -5.0
    errors, _ = run_checks(df, now=NOW)
    assert has(errors, "outside")


def test_too_many_nulls_is_an_error():
    df = make_df()
    df.loc[:7, "pm10"] = None  # 8 of 24 rows, about 33%
    errors, _ = run_checks(df, now=NOW)
    assert has(errors, "null")


def test_a_few_nulls_is_only_a_warning():
    df = make_df(hours=100)
    df.loc[5, "us_aqi"] = None  # 1 of 100 rows
    errors, warnings = run_checks(df, now=NOW)
    assert errors == []
    assert has(warnings, "null")


def test_gap_in_hourly_data_is_a_warning():
    df = make_df().drop(index=10).reset_index(drop=True)
    errors, warnings = run_checks(df, now=NOW)
    assert errors == []
    assert has(warnings, "gap")


def test_stale_data_is_an_error():
    errors, _ = run_checks(make_df(), now=pd.Timestamp("2026-11-12 12:00"))
    assert has(errors, "stale")
