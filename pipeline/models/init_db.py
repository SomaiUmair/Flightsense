"""Create the database tables for FlightSense.

Run once to create every model's table in PostgreSQL. Safe to re-run — existing
tables are skipped.
"""

from pipeline.models.database import Base, engine

# Importing the model registers it on Base.metadata; without this import,
# create_all() would have no tables to create.
from pipeline.models.flight import PriceQuote  # noqa: F401


def init_db() -> None:
    """Create all tables registered on Base."""
    # create_all issues CREATE TABLE for every table Base knows about.
    Base.metadata.create_all(bind=engine)
    print("Tables created (or already existed).")


if __name__ == "__main__":
    init_db()
