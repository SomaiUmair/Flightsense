# ml/models/predict.py
# Inference pipeline: LOAD the saved model -> predict prices for a flight across
# the days still left before departure -> recommend BOOK NOW or WAIT.
#
# THE IDEA:
#   The model predicts a price from features (days-to-departure, calendar, route).
#   So for one flight, we ask it: "what would the price be if seen today? in 3
#   days? in 10 days?" -- one guess per remaining day. The day with the lowest
#   predicted price is the best time to book. If that day is today -> BOOK NOW.
#
# NOTE: this reuses build_features() -- the SAME feature logic training used.
#   That's why features must line up: same code, same columns.

import pandas as pd                                       # DataFrame library
import joblib                                             # loads the model file train.py saved
from datetime import date, timedelta                      # for working with dates

from ml.features.build_features import build_features     # shared feature logic (same as training)
from ml.models.train import BASE_FEATURES, MODEL_PATH     # reuse the feature list + model file path


def load_model():                                         # read the trained model back off disk
    """Load the saved model bundle (the model + the columns it was trained on)."""
    if not MODEL_PATH.exists():                           # no file yet -> the model was never trained
        raise RuntimeError(f"No trained model at {MODEL_PATH}. Run: python -m ml.models.train")
    bundle = joblib.load(MODEL_PATH)                      # this is the dict train.py saved
    return bundle["model"], bundle["feature_columns"]     # hand back both pieces


def _candidate_rows(origin, destination, departure_date, today):  # build one row per remaining day
    """One synthetic row per day from today until departure ('if seen that day')."""
    days_left = (departure_date - today).days             # how many days until the flight
    rows = []                                             # collect the rows here
    for d in range(0, days_left + 1):                     # d = days-before-departure, from 0 up to days_left
        observed = departure_date - timedelta(days=d)     # the calendar date that is d days before departure
        rows.append({                                     # the columns build_features() needs (no price required)
            "origin": origin,
            "destination": destination,
            "departure_date": pd.Timestamp(departure_date),
            "observed_at": pd.Timestamp(observed),
        })
    return pd.DataFrame(rows)                              # turn the list of rows into a DataFrame


def predict_prices(origin, destination, departure_date, today=None):  # predicted price for each remaining day
    """Return a DataFrame: for each remaining day, the model's predicted price."""
    model, feature_columns = load_model()                 # 1. load the trained model + its column list
    if today is None:                                     # default "today" to the real current date
        today = date.today()

    candidates = _candidate_rows(origin, destination, departure_date, today)  # 2. build the candidate rows
    feats = build_features(candidates)                    # 3. SAME feature engineering used in training

    # 4. Build X exactly like training did: numeric features + one-hot route.
    route_dummies = pd.get_dummies(feats["route"], prefix="route")
    X = pd.concat([feats[BASE_FEATURES], route_dummies], axis=1)

    # 5. Line up columns with training. reindex adds any missing training columns
    #    (filled with 0) and drops unknown ones, so X matches what the model expects.
    X = X.reindex(columns=feature_columns, fill_value=0)

    feats["predicted_price"] = model.predict(X)           # 6. the model's price guess for each day
    return feats[["observed_at", "days_to_departure", "predicted_price"]]  # just the useful columns


def recommend(origin, destination, departure_date, today=None):  # turn predictions into advice
    """Return a dict recommending when to book, based on predicted prices."""
    if today is None:
        today = date.today()

    preds = predict_prices(origin, destination, departure_date, today)  # predicted price per remaining day
    cheapest = preds.loc[preds["predicted_price"].idxmin()]             # the row with the lowest predicted price
    best_day = cheapest["observed_at"].date()                          # the calendar date of that cheapest price

    # Today's own predicted price (the row where days_to_departure is largest = furthest from departure = today).
    today_row = preds.loc[preds["days_to_departure"].idxmax()]
    price_today = float(today_row["predicted_price"])

    return {                                              # a plain dict -> easy to print AND to return as JSON
        "route": f"{origin}-{destination}",
        "departure_date": str(departure_date),
        "predicted_price_today": round(price_today, 2),
        "cheapest_predicted_price": round(float(cheapest["predicted_price"]), 2),
        "best_day_to_book": str(best_day),
        # If the cheapest predicted day is today, book now; otherwise wait for it.
        "recommendation": "BOOK_NOW" if best_day <= today else "WAIT",
    }


if __name__ == "__main__":                                # demo when run directly
    result = recommend("YYC", "LHR", date(2026, 9, 1))    # try one of the tracked flights
    for key, value in result.items():                     # print the recommendation nicely
        print(f"{key:>25}: {value}")
