"""Load flight price history from PostgreSQL into pandas DataFrames.

The only ML module that talks to the database; downstream steps work on the
returned DataFrames.
"""

from datetime import date

import pandas as pd
from sqlalchemy import text

from pipeline.models.database import engine


def load_all_quotes() -> pd.DataFrame:
    """Load the entire price_quotes table as a DataFrame (oldest first)."""
    query = "SELECT * FROM price_quotes ORDER BY observed_at ASC"
    df = pd.read_sql(query, engine)

    # Coerce DB types to ML-friendly ones (Numeric -> float, dates -> datetime).
    df["price"] = df["price"].astype(float)
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    df["departure_date"] = pd.to_datetime(df["departure_date"])
    return df


def load_quotes_for_flight(
    origin: str, destination: str, departure_date: date
) -> pd.DataFrame:
    """Load the price history for one specific flight (oldest first)."""
    # Parameterized query (named placeholders) rather than string formatting.
    query = text(
        "SELECT * FROM price_quotes "
        "WHERE origin = :origin "
        "AND destination = :destination "
        "AND departure_date = :departure_date "
        "ORDER BY observed_at ASC"
    )
    params = {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
    }
    df = pd.read_sql(query, engine, params=params)

    df["price"] = df["price"].astype(float)
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    df["departure_date"] = pd.to_datetime(df["departure_date"])
    return df


if __name__ == "__main__":
    df = load_all_quotes()
    print(df.shape)
    print(df.dtypes)
    print(df.head())
