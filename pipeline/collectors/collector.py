"""Save flight prices to the database.

record_quote() persists one price and is the single write path used by the
ingestion step.
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
    """Save one flight price and return the persisted row."""
    # A session is one unit of work; the `with` block commits/closes cleanly.
    with SessionLocal() as session:
        quote = PriceQuote(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=price,
            currency=currency,
        )
        session.add(quote)
        session.commit()
        session.refresh(quote)  # reload to populate DB-generated id and observed_at
        return quote


if __name__ == "__main__":
    # Sample rows to check the function works end to end.
    samples = [
        ("YYC", "LHR", date(2026, 9, 1), 899.99, "CAD"),
        ("YYC", "LHR", date(2026, 9, 1), 875.50, "CAD"),
        ("YVR", "NRT", date(2026, 10, 15), 1120.00, "CAD"),
    ]
    for origin, destination, dep, price, currency in samples:
        saved = record_quote(origin, destination, dep, price, currency)
        print(f"Saved: {saved}")
