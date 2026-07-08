"""Database connection setup for FlightSense.

Central place that configures the PostgreSQL connection. Exposes the `engine`,
the `SessionLocal` session factory, and the `Base` class that models inherit
from — imported by the models, pipeline, and API so there is one shared setup.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load variables from .env so DATABASE_URL is available without hardcoding the
# connection string (and keeping it out of source control).
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Fail immediately with a clear message if the connection string is missing,
# rather than surfacing a confusing error later.
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Check that a .env file exists and contains it."
    )

# Create the engine once and share it app-wide. pool_pre_ping checks that a
# pooled connection is still alive before use, avoiding stale-connection errors.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory: other modules call SessionLocal() to open a database session.
SessionLocal = sessionmaker(bind=engine, autoflush=False)


# Base class that every table model inherits from; SQLAlchemy uses it to
# collect table metadata and map classes to tables.
class Base(DeclarativeBase):
    pass


def test_connection() -> bool:
    """Run a trivial query to confirm the database is reachable."""
    with engine.connect() as connection:
        # SELECT 1 is a no-op round-trip: if it returns, the connection works.
        result = connection.execute(text("SELECT 1"))
        return result.scalar() == 1


if __name__ == "__main__":
    if test_connection():
        print("Database connection successful.")
    else:
        print("Database connection failed: unexpected response.")
