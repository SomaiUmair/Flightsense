"""Live flight-price source: the Travelpayouts Data API.

Fetches recently-found one-way fares for tracked routes. Requires
TRAVELPAYOUTS_TOKEN in .env (free account at https://www.travelpayouts.com).
Prices come from real traveller searches cached over roughly the last 48
hours, so each run returns fares for whichever departure dates were searched
— many dates per route rather than one fixed date.

Replaced the Amadeus Self-Service API, decommissioned 2026-07-17; only this
module and the tracked-route list changed in the swap.
"""

import os
from datetime import date, datetime

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.travelpayouts.com"


def _get_token() -> str:
    """Return the Travelpayouts API token, failing fast if missing."""
    token = os.getenv("TRAVELPAYOUTS_TOKEN")
    if not token:
        raise RuntimeError(
            "TRAVELPAYOUTS_TOKEN is not set. Add it to your .env file."
        )
    return token


def get_live_prices(tracked_routes: list[dict], currency: str = "usd") -> list[dict]:
    """Return recently-found one-way fares for each tracked route.

    One quote per (route, departure date): the cheapest fare found for that
    date within the API's recent-search window.
    """
    headers = {"X-Access-Token": _get_token()}
    today = date.today()

    quotes = []
    for route in tracked_routes:
        params = {
            "origin": route["origin"],
            "destination": route["destination"],
            "currency": currency,
            "one_way": "true",
            "period_type": "year",  # any upcoming departure date
            "limit": 30,
            "sorting": "price",
        }
        response = requests.get(
            f"{BASE_URL}/v2/prices/latest",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        # Keep the cheapest fare per departure date; future flights only.
        cheapest_by_date: dict[date, float] = {}
        for entry in payload.get("data", []):
            if not entry.get("actual", True):
                continue  # the API marks stale finds actual=false
            depart = datetime.strptime(entry["depart_date"], "%Y-%m-%d").date()
            if depart < today:
                continue
            price = float(entry["value"])
            if depart not in cheapest_by_date or price < cheapest_by_date[depart]:
                cheapest_by_date[depart] = price

        for depart, price in sorted(cheapest_by_date.items()):
            quotes.append(
                {
                    "origin": route["origin"],
                    "destination": route["destination"],
                    "departure_date": depart,
                    "price": round(price, 2),
                    # Store the currency the API actually priced in, not the
                    # one requested — they can differ, and the row must stay
                    # honest.
                    "currency": payload.get("currency", currency).upper(),
                }
            )
    return quotes
