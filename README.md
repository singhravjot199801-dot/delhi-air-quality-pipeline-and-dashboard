# Delhi Air Quality Pipeline and Dashboard

An automated data pipeline that collects hourly air quality and weather data for Delhi, validates it, and stores it in Postgres every day. On top of the stored data I built a SQL analysis, a live dashboard, and a 24-hour PM2.5 forecasting experiment.

**Live dashboard:** https://delhi-air-quality-pipeline-and-dashboard.streamlit.app

**Question this project asks:** How do Delhi's PM2.5 levels vary by hour of day and weather, and can tomorrow's PM2.5 be forecast?

## Dashboard

An interactive Streamlit dashboard reads the stored data from Postgres through a read-only database user.

![Daily PM2.5 trend](docs/images/Delhi_Air_quality_Line_chart.png)

![PM2.5 by hour of day and wind speed](docs/images/Delhi_Air_quality_Column_chart.png)

![PM2.5 versus wind speed](docs/images/Delhi_Air_quality_Scatter_PLot.png)

## Architecture

```mermaid
flowchart LR
    A[Open-Meteo Air Quality API] --> C[ingest.py: fetch, clean, merge]
    B[Open-Meteo Weather API] --> C
    C --> D[quality.py: validation checks]
    D -->|checks pass| E[load.py: idempotent upsert]
    D -->|checks fail| X[Abort the run]
    E --> F[(Neon Postgres)]
    G[GitLab CI/CD daily schedule] --> C
    F -->|read-only user| H[dashboard.py: Streamlit]
    F --> I[SQL analysis and forecast notebook]
```

## What the pipeline does

1. **Ingest** (`ingest.py`): pulls hourly PM2.5, PM10, US AQI, temperature, humidity and wind speed from two Open-Meteo APIs, with automatic retries on temporary server errors. Timestamps are in Asia/Kolkata local time.
2. **Clean**: removes duplicate timestamps, drops the future hours the APIs return for the rest of today (forecasts are not stored as readings), and nulls out physically impossible values.
3. **Validate** (`quality.py`): blocks the load when the data is empty, has missing columns, duplicate or unsorted timestamps, out-of-range values, too many nulls, or is stale. Smaller issues such as gaps in the hourly series are logged as warnings.
4. **Load** (`load.py`): upserts into Postgres keyed on the timestamp, inside one transaction, so re-running the job never creates duplicates and a failed load leaves no partial data.
5. **Schedule** (`.gitlab-ci.yml`): GitLab CI/CD runs the tests and then the load every day. Each run re-fetches the last 7 days, so a missed day is filled in automatically.

## Tech stack

Python 3.12, pandas, requests, PostgreSQL (Neon), psycopg2, scikit-learn, pytest, Streamlit, GitLab CI/CD.

## Data sources

- [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- [Open-Meteo Weather API](https://open-meteo.com/en/docs)

## Findings

These come from the SQL queries in `analysis/` (notes in `docs/analysis-notes.md`) and cover hourly data from mid-September to mid-November 2026, the post-monsoon season. They show associations, not proof of cause.

- **Daily cycle:** PM2.5 is lowest around 13:00 to 14:00 (about 53 µg/m³) and highest around 22:00 to 23:00 (about 95 µg/m³), roughly 80% higher at night than at midday.
- **Wind:** PM2.5 falls as wind speed rises, from about 86 µg/m³ in calm conditions (under 5 km/h) to 72 at 5 to 10 km/h and 52 at 10 to 20 km/h, roughly 39% lower than in calm air. No hours in the data exceeded 20 km/h, and the windiest group has only 147 hours.
- **Weather correlations:** PM2.5 correlates moderately and negatively with temperature (-0.40) and wind speed (-0.34), and barely with humidity (0.11), so weather alone explains only part of the variation.

## Forecast experiment

I tested whether PM2.5 can be predicted 24 hours ahead, using only information available a day earlier (PM2.5 lags, the previous day's average, previous-day weather and hour of day). The split is by time, with the earliest 80% of hours for training and the latest 20% for testing, so no future information leaks into training. The code is in `notebooks/02_forecast.ipynb`.

| Model | MAE (µg/m³) | RMSE (µg/m³) |
|---|---|---|
| Baseline: same hour yesterday | 25.3 | 32.1 |
| Baseline: hourly average | 55.5 | 65.3 |
| Ridge regression | 37.9 | 46.7 |
| Gradient boosting | 56.1 | 70.4 |

**Result:** no model beat the "same hour yesterday" baseline.

**Why:** average PM2.5 was about 80% higher in the test period (123 µg/m³) than in the training period (68 µg/m³). Ridge regression under-predicted by about 36 µg/m³ on average, and apart from that bias its error spread was about the same as the baseline's (29.9 versus 30.7), so the lag and weather features added little beyond yesterday's value. Gradient boosting cannot predict beyond the range it saw in training, and the test period went above it. Predicting the change from yesterday's value instead of the level did not help.

**Limits:** about two months of data from one season, a single split, and a change in pollution level in the middle of the data.

## Data quality and testing

Nine pytest tests in `tests/test_quality.py` cover each validation rule using small synthetic datasets. The tests run on every push and before every scheduled load.

```bash
python -m pytest
```

## Run it locally

```bash
git clone https://gitlab.com/singhravjot199801/delhi-air-quality-pipeline-and-dashboard.git
cd delhi-air-quality-pipeline-and-dashboard
python -m venv .venv
.venv\Scripts\activate        # Windows. On Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file containing your Postgres connection string (this file is git-ignored):

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Then run:

```bash
python load.py                          # fetch, validate and load the last 7 days
python load.py --past-days 60           # load a longer history
python -m streamlit run dashboard.py    # open the dashboard locally
```

## Project structure

```
ingest.py              fetch, clean and merge the two sources
quality.py             data quality checks
load.py                idempotent Postgres load
dashboard.py           Streamlit dashboard reading from Postgres
tests/                 pytest tests for the quality checks
analysis/              SQL queries for exploratory analysis
notebooks/             data exploration and forecast experiment
docs/                  data notes, analysis notes and dashboard screenshots
.gitlab-ci.yml         CI pipeline: tests on push, daily scheduled load
requirements.txt       full local dependencies
requirements-ci.txt    slim dependencies used in CI
```

## Challenges and what I learned

- **Library compatibility:** my system Python was too new for pandas, which failed to install. I built the project in a Python 3.12 virtual environment and kept dependencies in `requirements.txt`.
- **Data validation paid off:** when I tried to backfill 90 days, the quality checks blocked the load because 30% of the weather rows were empty. I traced the gap to the oldest ~27 days of the request and loaded 60 days instead, so bad data never reached the database.
- **Idempotent loads:** the load upserts on the timestamp inside one transaction, so re-running it, or re-fetching overlapping days in the daily job, never creates duplicates.
- **Keeping secrets out of Git:** Windows saved my credentials file as `.env.txt`, which my `.gitignore` did not cover. I caught it with `git status` before committing, renamed and ignored it, and stored the database URL as a CI/CD variable for the scheduled job.
- **Least privilege for the public app:** the deployed dashboard connects with a read-only Postgres role, so it cannot change or delete data. Streamlit Community Cloud deploys from GitHub, so the dashboard is deployed from a copy of this repository there.
- **Honest evaluation:** building baselines first showed that my forecasting models did not beat "same hour yesterday". Diagnosing why (a shift in the pollution level between training and test periods) taught me more than a flattering result would have.

## Limitations

- The data covers about two months from one season, so the findings are not a year-round picture.
- The air quality values are modelled estimates provided by Open-Meteo rather than readings from individual ground monitors (see Open-Meteo's documentation for details).
- The forecast experiment uses a single time split.

## Roadmap

- Longer history from Open-Meteo's historical weather endpoint, to cover several seasons
- Walk-forward validation and an adaptive level correction for the forecast
- Alerting when a scheduled run fails