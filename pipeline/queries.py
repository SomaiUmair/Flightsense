"""Read flight prices back out of the database.

So far every script has WRITTEN rows. This one READS them. It answers the two
questions a price tracker exists to answer:
  1. What's the full price history for a flight?  (has it gone up or down?)
  2. What's the cheapest we've ever seen it?       (should I book now?)

These functions are also what our FastAPI routes will call later -- the API
just wraps these reads and returns them as JSON.
"""

from datetime import date

from pipeline.models.database import SessionLocal
from pipeline.models.flight import PriceQuote


def get_price_history(
    origin: str, destination: str, departure_date: date
) -> list[PriceQuote]:
    """Return every recorded price for one flight, oldest first.

    Ordering by observed_at turns a pile of rows into a timeline you can read
    top-to-bottom as the price changed.
    """
    with SessionLocal() as session:
        return (
            session.query(PriceQuote)
            # .filter narrows to just this route + date (the WHERE clause).
            .filter(
                PriceQuote.origin == origin,
                PriceQuote.destination == destination,
                PriceQuote.departure_date == departure_date,
            )
            # oldest observation first, so the list reads as a timeline.
            .order_by(PriceQuote.observed_at)
            .all()
        )


def get_cheapest(
    origin: str, destination: str, departure_date: date
) -> PriceQuote | None:
    """Return the single lowest-priced observation for one flight.

    Returns None if we've never recorded a price for it.
    """
    with SessionLocal() as session:
        return (
            session.query(PriceQuote)
            .filter(
                PriceQuote.origin == origin,
                PriceQuote.destination == destination,
                PriceQuote.departure_date == departure_date,
            )
            # cheapest first...
            .order_by(PriceQuote.price)
            # ...then take just the top row. .first() returns None if empty.
            .first()
        )


# Run directly to see the reads against whatever is already in the table.
if __name__ == "__main__":
    origin, destination, dep = "YYC", "LHR", date(2026, 9, 1)

    history = get_price_history(origin, destination, dep)
    print(f"📈 Price history for {origin}->{destination} on {dep}:")
    for q in history:
        print(f"   {q.observed_at:%Y-%m-%d %H:%M}  {q.price} {q.currency}")

    cheapest = get_cheapest(origin, destination, dep)
    if cheapest:
        print(f"💰 Cheapest seen: {cheapest.price} {cheapest.currency}")
    else:
        print("No prices recorded for that flight yet.")
