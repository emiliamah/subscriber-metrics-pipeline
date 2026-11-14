"""Load raw event CSVs into the staging table in Postgres.

The loading dock: rows go in exactly as they are in the CSV, bad ones included.

Safe to run more than once (idempotent): before loading a file, it deletes
any rows that came from that same file, so nothing gets counted twice.

Run from the project folder:
    python src/load_staging.py                  # load every CSV in data/raw
    python src/load_staging.py --date 2026-10-15   # load just one day
"""
import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# How Python finds the database: user:password@where:port/database_name
DATABASE_URL = "postgresql+psycopg2://pipeline:pipeline@localhost:5433/subscribers"

RAW_DIR = Path("data/raw")


def load_file(conn, path):
    """Load one CSV into staging.subscription_events. Returns the row count."""
    df = pd.read_csv(path, dtype=str)  # read everything as text, like a loading dock should
    df["source_file"] = path.name

    # 1. Remove anything already loaded from this file (makes re-runs safe)
    conn.execute(
        text("DELETE FROM staging.subscription_events WHERE source_file = :f"),
        {"f": path.name},
    )

    # 2. Insert the rows
    df.to_sql(
        "subscription_events",
        con=conn,
        schema="staging",
        if_exists="append",  # add to the existing table, don't replace it
        index=False,         # don't add pandas' row numbers as a column
    )
    return len(df)


def main():
    parser = argparse.ArgumentParser(description="Load raw CSVs into staging.")
    parser.add_argument("--date", help="load only this day, YYYY-MM-DD")
    args = parser.parse_args()

    if args.date:
        files = [RAW_DIR / f"events_{args.date}.csv"]
    else:
        files = sorted(RAW_DIR.glob("events_*.csv"))

    if not files or not files[0].exists():
        print("No CSV files found. Run src/generate_events.py first.")
        return

    engine = create_engine(DATABASE_URL)
    total = 0

    # engine.begin() opens a transaction: if anything fails, nothing is saved.
    with engine.begin() as conn:
        for path in files:
            count = load_file(conn, path)
            total += count
            print(f"Loaded {count:>4} rows from {path.name}")

    print(f"Done: {total} rows from {len(files)} files")


if __name__ == "__main__":
    main()
