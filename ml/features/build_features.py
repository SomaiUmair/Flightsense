# ml/features/build_features.py
# Feature engineering: turn raw price rows (a DataFrame from ml/data.py) into
# the numeric "features" a model can actually learn from.
#
# WHY THIS FILE EXISTS (and why it's shared):
#   A model can't learn from raw rows like "YYC->LHR, $899, seen 2026-07-06".
#   It needs NUMBERS that carry signal -- above all, "how many days before
#   departure was this price seen?" (prices tend to move as the date nears).
#   Both training AND prediction must build features the SAME way, so that logic
#   lives here, in ONE place, and both import it.
#
# INPUT:  a DataFrame of raw quotes (origin, destination, departure_date,
#         price, currency, observed_at) -- exactly what ml/data.py returns.
# OUTPUT: the same rows, plus new feature columns.

import pandas as pd                                   # DataFrame library
from ml.data import load_all_quotes                   # used only by the smoke test at the bottom


def build_features(df):                               # takes the raw quotes DataFrame, returns it with features added
    """Add model-ready feature columns to a raw quotes DataFrame."""

    df = df.copy()                                    # work on a copy so we never mutate the caller's DataFrame

    # --- normalize the two date columns so we can do clean date math ---
    # observed_at is timezone-aware (UTC); departure_date has no timezone.
    # utc=True makes both consistent, tz_localize(None) drops the timezone,
    # and normalize() throws away the time-of-day so we compare whole days.
    observed_day = pd.to_datetime(df["observed_at"], utc=True).dt.tz_localize(None).dt.normalize()
    departure_day = pd.to_datetime(df["departure_date"]).dt.normalize()

    # --- THE key feature: days between when we saw the price and the flight ---
    df["days_to_departure"] = (departure_day - observed_day).dt.days  # whole days, as an integer

    # --- calendar features: capture weekly/seasonal patterns in prices ---
    df["observed_dow"] = observed_day.dt.dayofweek    # day of week we saw it (0=Mon ... 6=Sun)
    df["observed_month"] = observed_day.dt.month      # month we saw it (1-12)
    df["departure_dow"] = departure_day.dt.dayofweek  # day of week the flight departs
    df["departure_month"] = departure_day.dt.month    # month the flight departs

    # --- a single label for the route (useful for grouping / encoding later) ---
    df["route"] = df["origin"] + "-" + df["destination"]  # e.g. "YYC-LHR"

    return df                                         # hand back the enriched DataFrame


if __name__ == "__main__":                            # only runs when you execute this file directly
    raw = load_all_quotes()                           # 1. load raw prices from the database (via ml/data.py)
    features = build_features(raw)                    # 2. turn them into features
    print(features.shape)                             # (rows, columns) -- should have MORE columns than raw
    print(features.columns.tolist())                  # list every column name, so you can see the new features
    print(features.head())                            # eyeball the first few rows
