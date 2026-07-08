"""Training pipeline: load data, build features, train an XGBoost model, save it.

Predicts price (regression) from days-to-departure, calendar, and route. Run
occasionally as more price history accumulates.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from ml.data import load_all_quotes
from ml.features.build_features import build_features

# Model is saved next to this file; feature list is reused by predict.py.
MODEL_PATH = Path(__file__).parent / "model.joblib"
BASE_FEATURES = ["days_to_departure", "observed_dow", "observed_month", "departure_dow", "departure_month"]


def train() -> None:
    """Train the price model on all stored history and save it to disk."""
    raw = load_all_quotes()
    features = build_features(raw)

    # A model needs real data; warn (and stop if we can't even split) otherwise.
    if len(features) < 10:
        print(f"Warning: only {len(features)} rows. Train after the scheduler has "
              "collected more history — a model on this little data is meaningless.")
        if len(features) < 2:
            return

    # Target is price; features are the numeric columns plus one-hot route
    # (the model needs numbers, and routes cost very differently).
    y = features["price"]
    route_dummies = pd.get_dummies(features["route"], prefix="route")
    X = pd.concat([features[BASE_FEATURES], route_dummies], axis=1)

    # Hold back 20% to measure accuracy on rows the model never saw.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Report average dollar error on the held-out test set.
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f"Trained on {len(X_train)} rows. Average error on test set: ${mae:.2f}")

    # Save the feature columns too: inference must reproduce this exact column set.
    joblib.dump({"model": model, "feature_columns": X.columns.tolist()}, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
