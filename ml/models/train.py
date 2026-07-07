# ml/models/train.py
# Training pipeline: load data -> build features -> train a model -> SAVE it.
# Run this occasionally (offline), as more price history accumulates.
#
# WHAT THE MODEL PREDICTS (the "target"):
#   price. Given features about a flight (how many days before departure, what
#   day/month, which route), the model learns to predict the fare. This is a
#   REGRESSION problem (predicting a number, not a yes/no).
#
# THE PIPELINE, IN ORDER:
#   load raw prices -> build features -> split into train/test -> fit model ->
#   check accuracy on the held-out test set -> save the model to a file.

import pandas as pd                                       # DataFrame library
import joblib                                             # saves/loads Python objects (our trained model) to a file
from pathlib import Path                                  # builds file paths that work on any OS
from xgboost import XGBRegressor                          # the model: gradient-boosted trees, strong on tabular data
from sklearn.model_selection import train_test_split      # splits data into a training part and a testing part
from sklearn.metrics import mean_absolute_error           # scores how far off predictions are, on average

from ml.data import load_all_quotes                       # step 1: get raw prices from the database
from ml.features.build_features import build_features     # step 2: turn them into model-ready features

# Where the trained model gets saved. Path(__file__).parent = this file's folder
# (ml/models), so the model lands right next to this script.
MODEL_PATH = Path(__file__).parent / "model.joblib"

# The numeric feature columns the model learns from (created in build_features).
BASE_FEATURES = ["days_to_departure", "observed_dow", "observed_month", "departure_dow", "departure_month"]


def train():                                              # the whole training run, top to bottom
    """Train the price model on all stored history and save it to disk."""

    raw = load_all_quotes()                               # 1. pull every price row out of PostgreSQL
    features = build_features(raw)                        # 2. add the feature columns

    # Guard: machine learning needs data. With almost none, training is pointless.
    if len(features) < 10:                                # fewer than 10 rows...
        print(f"⚠️  Only {len(features)} rows. Train after the scheduler has "
              "collected more history — a model on this little data is meaningless.")
        if len(features) < 2:                             # can't even split 0 or 1 rows -> stop
            return

    # 3a. TARGET (y): the thing we want to predict -- the price.
    y = features["price"]

    # 3b. FEATURES (X): the inputs the model learns from.
    #     One-hot encode `route` (turn "YYC-LHR" into 0/1 columns), because the
    #     model needs numbers, not text -- and different routes cost very
    #     differently, so the model should know which route each row is.
    route_dummies = pd.get_dummies(features["route"], prefix="route")
    X = pd.concat([features[BASE_FEATURES], route_dummies], axis=1)  # numeric features + route columns

    # 4. Split: train on most of the data, hold back 20% to test honestly on
    #    rows the model never saw. random_state makes the split reproducible.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 5. Create and fit the model -- this is where it actually "learns".
    model = XGBRegressor(n_estimators=100, random_state=42)  # 100 trees, fixed seed for reproducibility
    model.fit(X_train, y_train)                           # learn the price patterns from the training rows

    # 6. Evaluate: predict on the held-out test rows, measure average error.
    predictions = model.predict(X_test)                  # the model's guesses for unseen rows
    mae = mean_absolute_error(y_test, predictions)       # average dollars off (lower = better)
    print(f"Trained on {len(X_train)} rows. Average error on test set: ${mae:.2f}")

    # 7. Save BOTH the model AND the exact feature columns it was trained on.
    #    predict.py must feed columns in this same order/shape, so we store them
    #    together. (One-hot columns depend on which routes existed at training.)
    joblib.dump({"model": model, "feature_columns": X.columns.tolist()}, MODEL_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")


if __name__ == "__main__":                                # run the training when this file is executed directly
    train()
