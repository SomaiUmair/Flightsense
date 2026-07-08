"""SQLAlchemy models for FlightSense.

Defines the database tables as model classes that inherit from Base. Currently
just PriceQuote — one row per observed flight price.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.models.database import Base


class PriceQuote(Base):
    """A single flight price observed at one point in time.

    A new row is stored on every check, so a route's price history is all its
    rows ordered by observed_at.
    """

    __tablename__ = "price_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Airport codes are 3-letter IATA; indexed because we filter by route often.
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)
    departure_date: Mapped[date] = mapped_column(index=True)

    # Decimal (Numeric), not float: money must be exact (floats round).
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))

    # server_default + timezone=True: the DB stamps a consistent UTC-aware time
    # on insert, so every row is timestamped even if we don't set it.
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Composite index for the most common query: price history for one flight.
    __table_args__ = (
        Index("ix_route_departure", "origin", "destination", "departure_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<PriceQuote {self.origin}->{self.destination} "
            f"{self.departure_date} {self.price} {self.currency}>"
        )
