"""Ingestion: fetch current prices from the source and save them.

Split into fetch_prices() (the source) and ingest() (the save loop) so the data
source can change without touching the pipeline.
"""

from pipeline.collectors.collector import record_quote
from pipeline.collectors.flight_api import get_live_prices

# Routes we track. Travelpayouts keys prices by CITY code (YTO = all Toronto
# airports, LON = all London airports), so routes use city codes; each run
# returns fares for many departure dates per route.
TRACKED_ROUTES = [
    {"origin": "YYC", "destination": "LON"},  # Calgary -> London
    {"origin": "YVR", "destination": "TYO"},  # Vancouver -> Tokyo
    {"origin": "YTO", "destination": "PAR"},  # Toronto -> Paris
]


def fetch_prices() -> list[dict]:
    """Return recently-found fares for each tracked route."""
    # usd, not cad: Travelpayouts documents rub/usd/eur; the saver stores
    # whatever currency each quote reports.
    return get_live_prices(TRACKED_ROUTES, currency="usd")


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
