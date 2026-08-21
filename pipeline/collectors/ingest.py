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
    # Toronto
    {"origin": "YTO", "destination": "PAR"},
    {"origin": "YTO", "destination": "LON"},
    {"origin": "YTO", "destination": "NYC"},
    {"origin": "YTO", "destination": "LAX"},
    {"origin": "YTO", "destination": "MIA"},
    {"origin": "YTO", "destination": "CUN"},
    {"origin": "YTO", "destination": "ROM"},
    {"origin": "YTO", "destination": "DEL"},
    {"origin": "YTO", "destination": "DXB"},
    {"origin": "YTO", "destination": "TYO"},
    # Vancouver
    {"origin": "YVR", "destination": "TYO"},
    {"origin": "YVR", "destination": "LON"},
    {"origin": "YVR", "destination": "LAX"},
    {"origin": "YVR", "destination": "HKG"},
    {"origin": "YVR", "destination": "SYD"},
    {"origin": "YVR", "destination": "DEL"},
    {"origin": "YVR", "destination": "MNL"},
    # Calgary
    {"origin": "YYC", "destination": "LON"},
    {"origin": "YYC", "destination": "LAX"},
    {"origin": "YYC", "destination": "CUN"},
    {"origin": "YYC", "destination": "MEX"},
    # Montreal
    {"origin": "YMQ", "destination": "PAR"},
    {"origin": "YMQ", "destination": "LON"},
    {"origin": "YMQ", "destination": "CUN"},
    # Domestic Canada
    {"origin": "YTO", "destination": "YVR"},
    {"origin": "YTO", "destination": "YYC"},
    {"origin": "YMQ", "destination": "YVR"},
    {"origin": "YOW", "destination": "YTO"},
    # Sun destinations
    {"origin": "YTO", "destination": "PUJ"},
    {"origin": "YTO", "destination": "MBJ"},
    {"origin": "YMQ", "destination": "PUJ"},
    {"origin": "YVR", "destination": "HNL"},
    {"origin": "YYC", "destination": "PVR"},
    # US variety
    {"origin": "YTO", "destination": "CHI"},
    {"origin": "YTO", "destination": "SFO"},
    {"origin": "YVR", "destination": "SFO"},
    {"origin": "YYC", "destination": "LAS"},
    # Europe variety
    {"origin": "YTO", "destination": "BCN"},
    {"origin": "YTO", "destination": "LIS"},
    {"origin": "YTO", "destination": "DUB"},
    {"origin": "YTO", "destination": "IST"},
    {"origin": "YTO", "destination": "AMS"},
    # Asia
    {"origin": "YVR", "destination": "SEL"},
    {"origin": "YVR", "destination": "BKK"},
    # Ottawa and Halifax long-haul
    {"origin": "YOW", "destination": "LON"},
    {"origin": "YHZ", "destination": "LON"},
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
    print(f"Done - {len(quotes)} price(s) recorded this run.")


if __name__ == "__main__":
    ingest()
