"""Ingestion: fetch current prices from the source and save them.

Split into fetch_prices() (the source) and ingest() (the save loop) so the data
source can change without touching the pipeline.
"""

from datetime import date

from pipeline.collectors.collector import record_quote
from pipeline.collectors.flight_api import get_live_prices

# Routes and dates we track — the searches sent to the API each run.
TRACKED_FLIGHTS = [
    {"origin": "YYC", "destination": "LHR", "departure_date": date(2026, 9, 1)},
    {"origin": "YVR", "destination": "NRT", "departure_date": date(2026, 10, 15)},
    {"origin": "YYZ", "destination": "CDG", "departure_date": date(2026, 8, 20)},
]


def fetch_prices() -> list[dict]:
    """Return the current cheapest price for each tracked flight."""
    return get_live_prices(TRACKED_FLIGHTS, currency="CAD")


def ingest() -> None:
    """Fetch current prices and save each to the database."""
    quotes = fetch_prices()
    # Hand each fetched price to the saver.
    for q in quotes:
        saved = record_quote(
            q["origin"], q["destination"], q["departure_date"], q["price"], q["currency"]
        )
        print(f"Ingested: {saved}")
    print(f"Done — {len(quotes)} price(s) recorded this run.")


if __name__ == "__main__":
    ingest()
