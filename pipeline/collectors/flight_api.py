"""Live flight-price source: the Amadeus Self-Service API.

This replaces the mock. Given a route and date, it asks Amadeus for current
flight offers and returns the cheapest total fare, shaped exactly like the mock
did -- so ingest() does not change.

Setup (add to your .env):
    AMADEUS_CLIENT_ID=your_api_key
    AMADEUS_CLIENT_SECRET=your_api_secret

Get these by creating a free app at https://developers.amadeus.com. This module
uses the free TEST environment (test.api.amadeus.com), whose data is limited and
not real-time -- fine for building. Verify current endpoints, quotas, and terms
yourself; APIs change.
"""

import os

import requests
from dotenv import load_dotenv

# Make sure .env is loaded even if this module is imported on its own.
load_dotenv()

# Amadeus test environment. For production, this becomes https://api.amadeus.com
# (and you'd use production credentials).
BASE_URL = "https://test.api.amadeus.com"


def _get_access_token() -> str:
    """Exchange the API key + secret for a short-lived access token.

    Amadeus uses OAuth2 "client credentials": you POST your id and secret, and
    it returns a bearer token that every following request must carry. We fetch
    a fresh token each run, which is simple and fine for our low request volume.
    """
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are not set. "
            "Add them to your .env file."
        )

    response = requests.post(
        f"{BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    # Turn any HTTP error (bad key, rate limit) into a clear exception instead
    # of silently continuing with garbage.
    response.raise_for_status()
    return response.json()["access_token"]


def get_live_prices(tracked_flights: list[dict], currency: str = "CAD") -> list[dict]:
    """Fetch the cheapest current fare for each tracked flight.

    Returns a list of dicts in the SAME shape the mock produced:
        {origin, destination, departure_date, price, currency}
    so ingest() consumes it without any change.
    """
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    quotes = []
    for flight in tracked_flights:
        # The search parameters Amadeus expects. adults is required (>= 1).
        params = {
            "originLocationCode": flight["origin"],
            "destinationLocationCode": flight["destination"],
            "departureDate": flight["departure_date"].isoformat(),
            "adults": 1,
            "currencyCode": currency,
            "max": 20,  # cap how many offers come back
        }
        response = requests.get(
            f"{BASE_URL}/v2/shopping/flight-offers",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        # Amadeus returns matching offers under "data"; each offer has a
        # price.total (a string like "899.99").
        offers = response.json().get("data", [])
        if not offers:
            # No flights for this route/date this run -- skip, don't crash.
            continue

        # We record ONE price per flight per run: the cheapest available fare.
        cheapest = min(float(offer["price"]["total"]) for offer in offers)
        quotes.append(
            {
                "origin": flight["origin"],
                "destination": flight["destination"],
                "departure_date": flight["departure_date"],
                "price": round(cheapest, 2),
                "currency": currency,
            }
        )
    return quotes
