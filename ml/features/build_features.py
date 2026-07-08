"""Feature engineering for the price model.

Turns raw price rows into the numeric features the model uses. Shared by both
training and inference so features are always built the same way.
"""

import pandas as pd

from ml.data import load_all_quotes


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add model-ready feature columns to a raw quotes DataFrame."""
    df = df.copy()

    # observed_at is tz-aware (UTC), departure_date is not; normalize both to
    # naive whole days so the subtraction below is valid.
    observed_day = pd.to_datetime(df["observed_at"], utc=True).dt.tz_localize(None).dt.normalize()
    departure_day = pd.to_datetime(df["departure_date"]).dt.normalize()

    # Days until the flight — the strongest price signal.
    df["days_to_departure"] = (departure_day - observed_day).dt.days

    # Calendar features capture weekly and seasonal patterns.
    df["observed_dow"] = observed_day.dt.dayofweek
    df["observed_month"] = observed_day.dt.month
    df["departure_dow"] = departure_day.dt.dayofweek
    df["departure_month"] = departure_day.dt.month

    df["route"] = df["origin"] + "-" + df["destination"]
    return df


if __name__ == "__main__":
    features = build_features(load_all_quotes())
    print(features.shape)
    print(features.columns.tolist())
    print(features.head())
