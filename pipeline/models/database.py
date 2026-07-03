"""Database connection setup for FlightSense.

This module is the single place where we define how the application talks to
PostgreSQL. Everything else (models, pipeline scripts, the FastAPI app) imports
the engine, SessionLocal, and Base from here so there is exactly one source of
truth for the connection.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Read the .env file from disk and load its key/value pairs into the process
# environment (os.environ). This keeps the real connection string — including
# the password — out of source control. Call it once, at import time.
load_dotenv()

# Pull the connection string out of the environment. We read it into a constant
# here so the rest of the module references DATABASE_URL, not os.getenv calls
# scattered around.
DATABASE_URL = os.getenv("DATABASE_URL")

# Fail fast and loud if the variable is missing. Without this guard, a missing
# .env would surface later as a confusing SQLAlchemy error; this tells you
# exactly what's wrong at startup.
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Check that a .env file exists and contains it."
    )

# The engine is the core interface to the database. It manages a pool of
# connections and is meant to be created ONCE and shared for the life of the
# app — never per request, per query, or per script.
#
#   pool_pre_ping=True  -> before handing out a pooled connection, run a cheap
#                          check to make sure it's still alive. This avoids
#                          "server closed the connection" errors when a
#                          connection has gone stale (idle timeouts, DB restart).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# A factory that produces Session objects. Other modules do `db = SessionLocal()`
# to get a session, run their queries, then close it.
#
#   autoflush=False   -> don't auto-push pending changes to the DB before every
#                        query; we flush/commit explicitly so behavior is
#                        predictable.
#   autocommit=False  -> changes aren't committed until we call .commit(),
#                        which means each unit of work is a real transaction.
#   bind=engine       -> every session this factory creates uses our engine.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# The declarative base. Every table/model class (e.g. class FlightPrice(Base))
# will inherit from this. SQLAlchemy uses it to collect all model metadata so it
# can create tables and map rows to objects. In SQLAlchemy 2.0 the modern way to
# do this is to subclass DeclarativeBase rather than call declarative_base().
class Base(DeclarativeBase):
    pass


def test_connection() -> bool:
    """Open a connection, run a trivial query, and confirm the DB responds.

    Returns True on success and raises on failure. This is a smoke test you can
    run after configuring the environment, before wiring up real models.
    """
    # `with engine.connect()` borrows a connection from the pool and guarantees
    # it's returned (closed) even if an error is raised.
    with engine.connect() as connection:
        # In SQLAlchemy 2.0 raw SQL must be wrapped in text(). "SELECT 1" is the
        # standard no-op query: if it comes back, the round-trip works.
        result = connection.execute(text("SELECT 1"))
        # .scalar() pulls the single value (the 1) out of the result row.
        return result.scalar() == 1


# This block only runs when the file is executed directly
# (`python -m pipeline.models.database`), NOT when it's imported by other code.
# That lets the module double as a quick connection checker without side effects
# on import.
if __name__ == "__main__":
    if test_connection():
        print("✅ Database connection successful.")
    else:
        print("❌ Database connection failed: unexpected response.")
