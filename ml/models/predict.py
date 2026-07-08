"""Inference pipeline: load the model and recommend BOOK NOW or WAIT.

Predicts the fare for each remaining day before departure; the cheapest
predicted day is the best time to book.
"""

from datetime import date, timedelta

import joblib
import pandas as pd

from ml.features.build_features import build_features
from ml.models.train import BASE_FEATURES, MODEL_PATH


def load_model() -> tuple:
    """Load the saved model and the feature columns it was trained on."""
    if not MODEL_PATH.exists():
        raise RuntimeError(f"No trained model at {MODEL_PATH}. Run: python -m ml.models.train")
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"], bundle["feature_columns"]


def _candidate_rows(
    origin: str, destination: str, departure_date: date, today: date
) -> pd.DataFrame:
    """Build one synthetic row per day from today until departure."""
    days_left = (departure_date - today).days
    rows = []
    for d in range(0, days_left + 1):
        observed = departure_date - timedelta(days=d)
        rows.append({
            "origin": origin,
            "destination": destination,
            "departure_date": pd.Timestamp(departure_date),
            "observed_at": pd.Timestamp(observed),
        })
    return pd.DataFrame(rows)


def predict_prices(
    origin: str, destination: str, departure_date: date, today: date | None = None
) -> pd.DataFrame:
    """Return a DataFrame of predicted price per remaining day."""
    if today is None:
        today = date.today()
    if departure_date < today:
        raise ValueError("departure_date is in the past; nothing to predict")

    model, feature_columns = load_model()

    # Build candidate rows and run them through the SAME features as training.
    candidates = _candidate_rows(origin, destination, departure_date, today)
    feats = build_features(candidates)

    route_dummies = pd.get_dummies(feats["route"], prefix="route")
    X = pd.concat([feats[BASE_FEATURES], route_dummies], axis=1)
    # Align columns to training; the model requires the exact same feature set.
    X = X.reindex(columns=feature_columns, fill_value=0)

    feats["predicted_price"] = model.predict(X)
    return feats[["observed_at", "days_to_departure", "predicted_price"]]


def recommend(
    origin: str, destination: str, departure_date: date, today: date | None = None
) -> dict:
    """Return a dict recommending when to book, based on predicted prices."""
    if today is None:
        today = date.today()

    preds = predict_prices(origin, destination, departure_date, today)
    cheapest = preds.loc[preds["predicted_price"].idxmin()]
    best_day = cheapest["observed_at"].date()

    # Today is the row furthest from departure (largest days_to_departure).
    today_row = preds.loc[preds["days_to_departure"].idxmax()]
    price_today = float(today_row["predicted_price"])

    return {
        "route": f"{origin}-{destination}",
        "departure_date": str(departure_date),
        "predicted_price_today": round(price_today, 2),
        "cheapest_predicted_price": round(float(cheapest["predicted_price"]), 2),
        "best_day_to_book": str(best_day),
        # Book now if the cheapest predicted day is today; otherwise wait for it.
        "recommendation": "BOOK_NOW" if best_day <= today else "WAIT",
    }


if __name__ == "__main__":
    result = recommend("YYC", "LHR", date(2026, 9, 1))
    for key, value in result.items():
        print(f"{key:>25}: {value}")
