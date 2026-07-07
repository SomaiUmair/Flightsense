"""Ingest flight prices into PostgreSQL.

This is the "pull data IN" step of the pipeline. It has two halves:
  1. fetch_prices()  -- get the current prices from the source
  2. ingest()        -- hand each price to record_quote() to save it

The source is now the LIVE Amadeus flight-price API (see flight_api.py). When we
swapped the mock for the real API, ingest() and everything downstream did not
change -- only what fetch_prices() delegates to. That was the whole point of
keeping the two halves separate.
"""

from datetime import date

from pipeline.collectors.collector import record_quote
from pipeline.collectors.flight_api import get_live_prices

# The flights we track -- the routes/dates we ask the API about each run.
TRACKED_FLIGHTS = [
    {"origin": "YYC", "destination": "LHR", "departure_date": date(2026, 9, 1)},
    {"origin": "YVR", "destination": "NRT", "departure_date": date(2026, 10, 15)},
    {"origin": "YYZ", "destination": "CDG", "departure_date": date(2026, 8, 20)},
]


def fetch_prices() -> list[dict]:
    """Return the current cheapest price for each tracked flight.

    Delegates to the live Amadeus source, which returns dicts shaped
    {origin, destination, departure_date, price, currency} -- the same shape
    ingest() has always consumed.
    """
    return get_live_prices(TRACKED_FLIGHTS, currency="CAD")


def ingest() -> None:
    """Fetch the current prices and save every one to the database."""
    quotes = fetch_prices()
    for q in quotes:
        # record_quote() (from collector.py) is the saver. Ingestion doesn't
        # know or care how saving works -- it just fetches and hands off.
        saved = record_quote(
            q["origin"], q["destination"], q["departure_date"], q["price"], q["currency"]
        )
        print(f"✅ Ingested: {saved}")
    print(f"Done — {len(quotes)} price(s) recorded this run.")


# Run directly to pull the current (mock) prices and store them.
if __name__ == "__main__":
    ingest()
