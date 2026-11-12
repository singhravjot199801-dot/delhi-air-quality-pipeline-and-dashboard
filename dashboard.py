"""Streamlit dashboard for the Delhi air quality pipeline.

Run locally (project folder, virtual environment active):
    python -m streamlit run dashboard.py

The database URL is read from the DATABASE_URL environment variable
(or a local .env file), or from Streamlit secrets when deployed.
"""
import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

TABLE = "delhi_air_weather"
PM25_YARDSTICK = 60  # India's 24-hour PM2.5 standard in ug/m3, used as a rough yardstick

st.set_page_config(page_title="Delhi Air Quality", layout="wide")


def get_database_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return None


@st.cache_data(ttl=3600)
def load_data(url: str) -> pd.DataFrame:
    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT time, pm2_5, pm10, us_aqi, temperature_2m, "
                f"relative_humidity_2m, wind_speed_10m FROM {TABLE} ORDER BY time"
            )
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=columns)


def aqi_category(aqi) -> str:
    if pd.isna(aqi):
        return "n/a"
    for limit, label in [
        (50, "Good"),
        (100, "Moderate"),
        (150, "Unhealthy for sensitive groups"),
        (200, "Unhealthy"),
        (300, "Very unhealthy"),
    ]:
        if aqi <= limit:
            return label
    return "Hazardous"


st.title("Delhi Air Quality")
st.caption("Hourly PM2.5, AQI and weather, collected daily by an automated pipeline (Open-Meteo data)")

url = get_database_url()
if not url:
    st.error("DATABASE_URL was not found. Add it to your .env file or to Streamlit secrets.")
    st.stop()

try:
    df = load_data(url)
except Exception as exc:
    st.error(f"Could not load data from the database ({type(exc).__name__}).")
    st.stop()

if df.empty:
    st.warning("The table is empty. Run load.py first.")
    st.stop()

# ---- Sidebar filter ----
min_day, max_day = df["time"].min().date(), df["time"].max().date()
dates = st.sidebar.date_input(
    "Date range", value=(min_day, max_day), min_value=min_day, max_value=max_day
)
if not isinstance(dates, tuple) or len(dates) != 2:
    st.info("Select both a start and an end date.")
    st.stop()
start, end = dates

data = df[(df["time"].dt.date >= start) & (df["time"].dt.date <= end)].copy()
if data.empty:
    st.warning("No data in the selected range.")
    st.stop()

# ---- Headline numbers ----
latest = data.iloc[-1]
share_high = (data["pm2_5"] > PM25_YARDSTICK).mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest PM2.5 (ug/m3)", f"{latest['pm2_5']:.0f}", aqi_category(latest["us_aqi"]), delta_color="off")
c2.metric("Average PM2.5 (ug/m3)", f"{data['pm2_5'].mean():.0f}")
c3.metric("Peak PM2.5 (ug/m3)", f"{data['pm2_5'].max():.0f}")
c4.metric(f"Hours above {PM25_YARDSTICK} ug/m3", f"{share_high:.0%}")

# ---- Trend ----
st.subheader("Daily PM2.5 trend")
daily = data.set_index("time")["pm2_5"].resample("D").mean()
trend = pd.DataFrame({"Daily average": daily, "7-day average": daily.rolling(7, min_periods=1).mean()})
st.line_chart(trend)

# ---- Hour of day and wind ----
left, right = st.columns(2)

with left:
    st.subheader("PM2.5 by hour of day")
    by_hour = data.groupby(data["time"].dt.hour)["pm2_5"].mean()
    by_hour.index.name = "hour of day"
    st.bar_chart(by_hour)

with right:
    st.subheader("PM2.5 by wind speed")
    bands = pd.cut(
        data["wind_speed_10m"],
        bins=[0, 5, 10, 20, float("inf")],
        labels=["1: under 5 km/h", "2: 5-10 km/h", "3: 10-20 km/h", "4: 20+ km/h"],
        right=False,
        include_lowest=True,
    )
    by_wind = data.groupby(bands, observed=True)["pm2_5"].mean()
    by_wind.index.name = "wind speed"
    st.bar_chart(by_wind)

# ---- Weather relationship ----
st.subheader("PM2.5 versus wind speed")
st.scatter_chart(data, x="wind_speed_10m", y="pm2_5")

st.subheader("Correlation of PM2.5 with weather")
corr = (
    data[["pm2_5", "wind_speed_10m", "temperature_2m", "relative_humidity_2m"]]
    .corr()["pm2_5"]
    .drop("pm2_5")
    .round(2)
    .rename("correlation")
)
st.dataframe(corr)

st.caption(f"Data from {data['time'].min():%d %b %Y} to {data['time'].max():%d %b %Y}. Refreshes hourly from the database.")
