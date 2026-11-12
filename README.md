# Delhi Air Quality Pipeline and Dashboard

An automated data pipeline that collects hourly air quality and weather data for Delhi, validates it, and stores it in Postgres every day. The stored data supports analysis of how PM2.5 varies with season, time of day and weather, and forecasting of next-day AQI.

**Question this project answers:** How do Delhi's PM2.5 levels vary by season, time of day and weather, and can tomorrow's AQI be forecast?

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
```


## Dashboard

An interactive Streamlit dashboard reads the stored data from Postgres.

![Daily PM2.5 trend](docs/images/Delhi_Air_quality_Line_chart.png)

![PM2.5 by hour of day and wind speed](docs/images/Delhi_Air_quality_Column_chart.png)

![PM2.5 versus wind speed](docs/images/Delhi_Air_quality_Scatter_PLot.png)

Run it locally with `python -m streamlit run dashboard.py`.


## What the pipeline does

1. **Ingest** (`ingest.py`): pulls hourly PM2.5, PM10, US AQI, temperature, humidity and wind speed from two Open-Meteo APIs, with automatic retries on temporary server errors. Timestamps are in Asia/Kolkata local time.
2. **Clean**: removes duplicate timestamps, drops the future hours the APIs return for the rest of today (forecasts are not stored as readings), and nulls out physically impossible values.
3. **Validate** (`quality.py`): blocks the load when the data is empty, has missing columns, duplicate or unsorted timestamps, out-of-range values, too many nulls, or is stale. Smaller issues such as gaps in the hourly series are logged as warnings.
4. **Load** (`load.py`): upserts into Postgres keyed on the timestamp, inside one transaction, so re-running the job never creates duplicates and a failed load leaves no partial data.
5. **Schedule** (`.gitlab-ci.yml`): GitLab CI/CD runs the tests and then the load every day. Each run re-fetches the last 7 days, so a missed day is filled in automatically.

## Tech stack

Python 3.12, pandas, requests, PostgreSQL (Neon), psycopg2, pytest, GitLab CI/CD.

## Data sources

- [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- [Open-Meteo Weather API](https://open-meteo.com/en/docs)

## Data quality and testing

Nine pytest tests in `tests/test_quality.py` cover each validation rule using small synthetic datasets. The tests run on every push and before every scheduled load.

```bash
python -m pytest
```

## Run it locally

```bash
git clone <this-repo-url>
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
python load.py                  # fetch, validate and load the last 7 days
python load.py --past-days 30   # load a longer history
```

## Project structure

```
ingest.py              fetch, clean and merge the two sources
quality.py             data quality checks
load.py                idempotent Postgres load
tests/                 pytest tests for the quality checks
notebooks/             exploratory analysis of the raw data
docs/data-notes.md     notes on the sources, units and quirks I found
.gitlab-ci.yml         CI pipeline: tests on push, daily scheduled load
requirements.txt       full local dependencies
requirements-ci.txt    slim dependencies used in CI
```

## Findings

*Fill this in once the analysis is done.*

- [Key pattern 1, for example how PM2.5 differs by season, with a number]
- [Key pattern 2, for example the relationship between wind speed and PM2.5]
- [Forecast result, for example model error compared with a simple baseline]

## Challenges and what I learned

*Fill this in with your own experience. Ideas:*

- [A data quirk you found in the APIs and how you handled it]
- [A design decision, such as why the load is an idempotent upsert]
- [A deployment problem you solved]

## Roadmap

- SQL analysis models on top of the stored data
- Interactive dashboard
- Next-day AQI forecast with evaluation against a baseline
