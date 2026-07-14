"""Read flight prices from the database.

The read side of the pipeline: price history and cheapest fare for a flight.
These functions back the API's price endpoints.
"""

from datetime import date

from sqlalchemy import select

from pipeline.models.database import SessionLocal
from pipeline.models.flight import PriceQuote


def get_price_history(
    origin: str, destination: str, departure_date: date
) -> list[PriceQuote]:
    """Return every recorded price for one flight, oldest first."""
    stmt = (
        select(PriceQuote)
        .where(
            PriceQuote.origin == origin,
            PriceQuote.destination == destination,
            PriceQuote.departure_date == departure_date,
        )
        .order_by(PriceQuote.observed_at)
    )
    with SessionLocal() as session:
        return list(session.scalars(stmt))


def get_cheapest(
    origin: str, destination: str, departure_date: date
) -> PriceQuote | None:
    """Return the lowest-priced observation for one flight, or None."""
    stmt = (
        select(PriceQuote)
        .where(
            PriceQuote.origin == origin,
            PriceQuote.destination == destination,
            PriceQuote.departure_date == departure_date,
        )
        .order_by(PriceQuote.price)
        .limit(1)
    )
    with SessionLocal() as session:
        return session.scalars(stmt).first()


if __name__ == "__main__":
    origin, destination, dep = "YTO", "PAR", date(2026, 9, 20)

    history = get_price_history(origin, destination, dep)
    print(f"Price history for {origin}->{destination} on {dep}:")
    for q in history:
        print(f"   {q.observed_at:%Y-%m-%d %H:%M}  {q.price} {q.currency}")

    cheapest = get_cheapest(origin, destination, dep)
    if cheapest:
        print(f"Cheapest seen: {cheapest.price} {cheapest.currency}")
    else:
        print("No prices recorded for that flight yet.")
