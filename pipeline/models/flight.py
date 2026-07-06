"""Database models for FlightSense.

This is the schema layer. Each class here maps to one table in PostgreSQL.
The classes inherit from Base (defined in database.py), which is how SQLAlchemy
discovers them and knows how to create the tables and map rows to objects.
"""

from datetime import date, datetime

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.models.database import Base


class PriceQuote(Base):
    """A single flight price observed at one point in time.

    One row = "on <observed_at>, a flight from <origin> to <destination>
    departing <departure_date> cost <price> <currency>." Because we store a new
    row every time we check, the price history for any route is just all the
    rows for that route ordered by observed_at. That history is what makes
    FlightSense a *tracker* rather than a static price list.
    """

    __tablename__ = "price_quotes"

    # Surrogate primary key. An auto-incrementing integer that uniquely
    # identifies each row. We use a synthetic id rather than a natural key
    # because the same route/date will legitimately appear many times.
    id: Mapped[int] = mapped_column(primary_key=True)

    # IATA airport codes are always 3 letters (YYC, LHR). String(3) documents
    # that constraint and keeps the column tight. index=True on both because we
    # will constantly filter by route.
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)

    # The date the flight departs (no time component needed).
    departure_date: Mapped[date] = mapped_column(index=True)

    # Money. Numeric(10, 2) stores an exact decimal with 2 decimal places — up
    # to 99,999,999.99. We deliberately avoid Float for money because floats
    # introduce rounding errors (0.1 + 0.2 != 0.3); Numeric is exact.
    price: Mapped[float] = mapped_column(Numeric(10, 2))

    # ISO 4217 currency code (CAD, USD, GBP). A price is meaningless without it.
    currency: Mapped[str] = mapped_column(String(3))

    # When WE recorded this price. server_default=func.now() means PostgreSQL
    # stamps the current time on insert, so we can't forget to set it and every
    # row gets a consistent, DB-authoritative timestamp. timezone=True stores it
    # as timestamptz (UTC-aware), which avoids timezone ambiguity later.
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # A composite index for the most common query: "show me the price history
    # for this exact route + departure date, over time." A single combined index
    # serves that lookup far better than three separate ones.
    __table_args__ = (
        Index("ix_route_departure", "origin", "destination", "departure_date"),
    )

    def __repr__(self) -> str:
        # A readable representation for logs and debugging (what you see when you
        # print a PriceQuote), instead of the default <object at 0x...>.
        return (
            f"<PriceQuote {self.origin}->{self.destination} "
            f"{self.departure_date} {self.price} {self.currency}>"
        )
