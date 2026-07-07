"""Reusable collector for saving flight prices.

This is the grown-up version of save_quote.py. Instead of one hardcoded row,
it exposes a `record_quote(...)` function that saves ANY price you hand it.
Later, a real flight-price API will call this function once per price it fetches
-- the API becomes the source, this stays the saver.
"""

from datetime import date

from pipeline.models.database import SessionLocal
from pipeline.models.flight import PriceQuote


def record_quote(
    origin: str,
    destination: str,
    departure_date: date,
    price: float,
    currency: str,
) -> PriceQuote:
    """Save one flight price to the database and return the saved row.

    Takes the flight details as arguments (not hardcoded), so the same function
    works for any route, any price, called from anywhere.
    """
    # Open a session (one conversation with the DB); the `with` block closes it
    # for us even if something fails partway through.
    with SessionLocal() as session:
        # Build the row from the arguments we were given.
        quote = PriceQuote(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=price,
            currency=currency,
        )
        session.add(quote)      # stage it
        session.commit()        # write it to Postgres for real
        session.refresh(quote)  # pull back the DB-filled id + observed_at
        return quote


# Run directly to prove the function works with a couple of sample prices.
# These sample rows stand in until we connect a real flight-price API.
if __name__ == "__main__":
    samples = [
        ("YYC", "LHR", date(2026, 9, 1), 899.99, "CAD"),
        ("YYC", "LHR", date(2026, 9, 1), 875.50, "CAD"),  # same flight, cheaper later
        ("YVR", "NRT", date(2026, 10, 15), 1120.00, "CAD"),
    ]

    for origin, destination, dep, price, currency in samples:
        saved = record_quote(origin, destination, dep, price, currency)
        print(f"✅ Saved: {saved}")
