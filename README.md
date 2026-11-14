# Subscriber Metrics Pipeline

A batch ETL pipeline that turns raw subscription events (signups, upgrades, downgrades, cancellations) into daily subscriber metrics like active subscribers, churn rate, and net adds, with automated data quality checks.

**Status:** In progress

## Stack
Python, pandas, SQL, PostgreSQL (Docker), pytest

## Architecture
1. Generate simulated subscription events (CSV)
2. Load raw events into a PostgreSQL staging table
3. Run data quality checks (critical failures stop the run)
4. Transform clean data into a star schema
5. Build a daily subscriber metrics mart

## Run locally
```bash
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```