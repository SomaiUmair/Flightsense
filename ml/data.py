# ml/data.py
# Data loader: read flight price history out of PostgreSQL into a pandas
# DataFrame. This is the only ML file that talks to the database.
#
# Planned functions:
#   load_all_quotes()            -> DataFrame   (all history, for training)
#   load_quotes_for_flight(...)  -> DataFrame   (one flight, for inference)

#Import libraries
import pandas as pd                                  # the DataFrame library; `pd` is the standard nickname
from pipeline.models.database import engine          # reuse the ONE database connection we already built
from sqlalchemy import text                          # wraps SQL strings so we can pass safe, named parameters


def load_all_quotes():                               # define the function; no arguments -> it loads everything
    """Load the entire price_quotes table as a DataFrame (oldest first)."""  # what the function does (shows on hover)

    query = "SELECT * FROM price_quotes ORDER BY observed_at ASC"  # SQL: every column, sorted oldest -> newest

    df = pd.read_sql(query, engine)                  # run the query over our engine; pandas returns a DataFrame

    # --- type cleanup: make DB types friendly for machine learning ---
    df["price"] = df["price"].astype(float)          # Numeric comes out as Decimal/object -> force real float
    df["observed_at"] = pd.to_datetime(df["observed_at"])       # ensure this column is a real datetime
    df["departure_date"] = pd.to_datetime(df["departure_date"]) # ensure this is a real datetime too (for date math)

    return df                                        # hand the cleaned DataFrame back to the caller


def load_quotes_for_flight(origin, destination, departure_date):  # one specific flight: route + date come in as args
    """Load the price history for ONE specific flight (oldest first)."""  # docstring

    query = text(                                    # text() lets us use safe :named placeholders instead of gluing values in
        "SELECT * FROM price_quotes "                # every column...
        "WHERE origin = :origin "                    # ...only this origin...
        "AND destination = :destination "            # ...this destination...
        "AND departure_date = :departure_date "      # ...this departure date...
        "ORDER BY observed_at ASC"                   # ...sorted oldest -> newest
    )

    params = {                                       # the actual values that fill the :placeholders above
        "origin": origin,                            # :origin        <- origin argument
        "destination": destination,                  # :destination   <- destination argument
        "departure_date": departure_date,            # :departure_date <- departure_date argument
    }

    df = pd.read_sql(query, engine, params=params)   # run the parameterized query; pandas returns a DataFrame

    # --- same type cleanup as above ---
    df["price"] = df["price"].astype(float)          # Decimal/object -> float
    df["observed_at"] = pd.to_datetime(df["observed_at"])       # -> datetime
    df["departure_date"] = pd.to_datetime(df["departure_date"]) # -> datetime

    return df                                        # hand the cleaned DataFrame back


if __name__ == "__main__":                           # only runs when you execute this file directly
    df = load_all_quotes()                           # load everything...
    print(df.shape)                                  # (number of rows, number of columns)
    print(df.dtypes)                                 # the type of each column  <- check `price` is float64
    print(df.head())                                 # the first 5 rows, to eyeball the data
