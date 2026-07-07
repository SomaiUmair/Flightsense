"""Ingest flight prices into PostgreSQL.

This is the "pull data IN" step of the pipeline. It has two halves:
  1. fetch_prices()  -- get the current prices from a source
  2. ingest()        -- hand each price to record_quote() to save it

Right now the source is a MOCK: fetch_prices() makes up realistic fares so we
can build and run the whole pipeline without depending on an external service.
To go live, replace ONLY fetch_prices() with real flight-API calls. ingest()
and everything downstream stay exactly the same -- that's the whole point of
keeping the two halves separate.
"""

import random
from datetime import date

from pipeline.collectors.collector import record_quote

# The flights we track. A real API call would use these as its search inputs
# (which route, which date). base_price is only here for the mock, to jitter
# around -- a real source wouldn't need it.
TRACKED_FLIGHTS = [
    {"origin": "YYC", "destination": "LHR", "departure_date": date(2026, 9, 1), "base_price": 900.0},
    {"origin": "YVR", "destination": "NRT", "departure_date": date(2026, 10, 15), "base_price": 1150.0},
    {"origin": "YYZ", "destination": "CDG", "departure_date": date(2026, 8, 20), "base_price": 780.0},
]


def fetch_prices() -> list[dict]:
    """Return the current price for each tracked flight.

    *** MOCK SOURCE — this is the ONE function you replace to go live. ***

    It returns each flight's price jittered slightly around a base value, so
    running ingest repeatedly looks like real prices drifting up and down over
    time. A real version would call a flight API here and map its response into
    these same dicts.
    """
    quotes = []
    for flight in TRACKED_FLIGHTS:
        # +/- $50 of random movement so each run records a different price.
        price = round(flight["base_price"] + random.uniform(-50, 50), 2)
        quotes.append(
            {
                "origin": flight["origin"],
                "destination": flight["destination"],
                "departure_date": flight["departure_date"],
                "price": price,
                "currency": "CAD",
            }
        )
    return quotes


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
