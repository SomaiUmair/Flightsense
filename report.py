"""Pull current fares for all tracked routes, then print dataset stats.

Run from the repo root: python report.py
Needs the same .env as the rest of the project (DATABASE_URL and
TRAVELPAYOUTS_TOKEN).
"""

import os

from dotenv import load_dotenv
import psycopg2

from pipeline.collectors.ingest import ingest


def main() -> None:
    print("=== PULL ===", flush=True)
    ingest()

    print("\n=== DATASET ===", flush=True)
    load_dotenv()
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*), MIN(observed_at)::date, MAX(observed_at)::date "
        "FROM price_quotes"
    )
    total, first, last = cur.fetchone()
    print(f"total rows: {total:,}   window: {first} -> {last}")

    cur.execute(
        "SELECT observed_at::date, COUNT(*) FROM price_quotes "
        "GROUP BY 1 ORDER BY 1 DESC LIMIT 5"
    )
    print("last five collection days:")
    for day, n in cur.fetchall():
        print(f"  {day}: {n}")


if __name__ == "__main__":
    main()
