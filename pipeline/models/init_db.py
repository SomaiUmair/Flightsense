"""Create the database tables for FlightSense.

Run this once to build every table defined in our models inside PostgreSQL.
It reads the table blueprints (the model classes) and creates any that don't
already exist yet. Safe to run again — it skips tables that are already there.
"""

# The engine is our connection to PostgreSQL, and Base holds the record of
# every table we've defined. Both come from database.py.
from pipeline.models.database import Base, engine

# Import the model so that defining `class PriceQuote(Base)` actually runs.
# That line is what registers the table with Base. If we don't import it here,
# Base doesn't know the table exists and create_all() would build nothing.
from pipeline.models.flight import PriceQuote  # noqa: F401


def init_db() -> None:
    """Create all tables that inherit from Base."""
    # metadata is Base's catalogue of known tables. create_all() looks at that
    # catalogue and issues the CREATE TABLE commands to Postgres via the engine.
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created (or already existed).")


# Only runs when you execute this file directly, not when it's imported.
if __name__ == "__main__":
    init_db()
