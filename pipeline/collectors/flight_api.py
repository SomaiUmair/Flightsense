"""Live flight-price source: the Amadeus Self-Service API.

Fetches current fares for tracked flights. Requires AMADEUS_CLIENT_ID and
AMADEUS_CLIENT_SECRET in .env (create a free app at https://developers.amadeus.com).
Targets the test environment, whose data is limited and not real-time.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Amadeus test environment; production would use https://api.amadeus.com.
BASE_URL = "https://test.api.amadeus.com"


def _get_access_token() -> str:
    """Exchange the API key/secret for a short-lived OAuth2 bearer token."""
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are not set. "
            "Add them to your .env file."
        )

    # OAuth2 client-credentials: POST id/secret, receive a bearer token.
    response = requests.post(
        f"{BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_live_prices(tracked_flights: list[dict], currency: str = "CAD") -> list[dict]:
    """Return the cheapest current fare per tracked flight."""
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    quotes = []
    for flight in tracked_flights:
        # Search parameters Amadeus expects; adults is required.
        params = {
            "originLocationCode": flight["origin"],
            "destinationLocationCode": flight["destination"],
            "departureDate": flight["departure_date"].isoformat(),
            "adults": 1,
            "currencyCode": currency,
            "max": 20,
        }
        response = requests.get(
            f"{BASE_URL}/v2/shopping/flight-offers",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()

        offers = response.json().get("data", [])
        if not offers:
            continue  # no flights for this route/date this run

        # Record one price per flight: the cheapest available fare.
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
