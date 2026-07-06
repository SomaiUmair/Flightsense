"""Save a flight price to the database, then read it back.

This is the first working piece of the pipeline. It proves the whole chain
works end to end: connect -> write a row -> read it back. Every real collector
we write later will follow this same open-session / add / commit pattern.
"""

from datetime import date

from pipeline.models.database import SessionLocal
from pipeline.models.flight import PriceQuote


def save_quote() -> None:
    """Insert one PriceQuote row, then fetch all rows and print them."""

    # Open a session. This is one "conversation" with the database. We use a
    # `with` block so the session is always closed for us at the end, even if
    # something goes wrong in the middle.
    with SessionLocal() as session:

        # Build a row as a plain Python object. Nothing has touched the database
        # yet — this just exists in memory. We don't set id or observed_at:
        # Postgres fills those in for us (auto id, server default timestamp).
        quote = PriceQuote(
            origin="YYC",
            destination="LHR",
            departure_date=date(2026, 9, 1),
            price=899.99,
            currency="CAD",
        )

        # Stage the new row with the session ("I intend to save this").
        session.add(quote)

        # Commit the transaction. THIS is the moment the row is actually written
        # to Postgres. Before commit, nothing is saved.
        session.commit()

        print("✅ Saved one quote.")

        # Now read back everything in the table to confirm it's really there.
        # .scalars().all() returns the rows as PriceQuote objects in a list.
        all_quotes = session.query(PriceQuote).all()
        print(f"📋 {len(all_quotes)} row(s) in price_quotes:")
        for q in all_quotes:
            # Uses the __repr__ we defined on the model for a readable line.
            print(f"   {q}")


# Only runs when you execute this file directly, not when it's imported.
if __name__ == "__main__":
    save_quote()
