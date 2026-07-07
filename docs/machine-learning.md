# FlightSense — Machine Learning

This document explains the machine learning layer: how FlightSense learns from
stored price history and turns it into a "book now or wait" recommendation. It
reads from the same PostgreSQL warehouse the data pipeline fills; it does not
touch ingestion.

## Goal

Given a flight (route + departure date), recommend whether to **book now** or
**wait** for a better price. The model does this by predicting the fare, then
comparing the predicted price across the days still left before departure.

## Problem framing

- **Type:** regression — the model predicts a *number* (the price), not a
  yes/no.
- **Target (`y`):** `price`.
- **Features (`X`):** signals derived from each price observation — above all
  `days_to_departure`, plus calendar features and the route.

## The two pipelines

Machine learning is two separate flows that run at different times:

```
TRAINING  (offline, occasional)   load → features → train → SAVE model file
INFERENCE (on demand)             build features → LOAD model file → predict
```

They share one thing that must be identical in both: **feature engineering**.
If training and inference build features differently, predictions are garbage.
That shared logic lives in `ml/features/build_features.py`, and both pipelines
import it. The saved model file (`ml/models/model.joblib`) is the handoff
between the two.

## Components

| File | Role |
|------|------|
| `ml/data.py` | Loads price history from PostgreSQL into a pandas DataFrame. The only ML file that touches the database. |
| `ml/features/build_features.py` | Turns raw price rows into model features. **Shared** by training and inference. |
| `ml/models/train.py` | Training pipeline: load → features → train/test split → fit XGBoost → evaluate → save model + feature columns. |
| `ml/models/predict.py` | Inference pipeline: load model → predict prices across remaining days → recommend BOOK NOW / WAIT. |
| `backend/main.py` (`/predict`) | Serves the recommendation as JSON over HTTP. |

## Features

Built in `build_features()` from each raw price row:

| Feature | Meaning |
|---------|---------|
| `days_to_departure` | Days between when the price was observed and the flight. The strongest signal. |
| `observed_dow`, `observed_month` | When the price was seen (weekly/seasonal patterns). |
| `departure_dow`, `departure_month` | When the flight departs. |
| `route` | Origin-destination label (e.g. `YYC-LHR`), one-hot encoded before training. |

## How training works (`train.py`)

1. Load all history (`load_all_quotes`) and build features.
2. Guard: if there are very few rows, warn — a model trained on little data is
   meaningless.
3. Split `X` / `y`, then split into train (80%) and test (20%) so accuracy is
   measured on rows the model never saw.
4. Fit an `XGBRegressor`.
5. Evaluate with mean absolute error (average dollars off) on the test set.
6. Save `{model, feature_columns}` to `model.joblib`. The feature columns are
   saved so inference can reproduce the exact same input shape.

## How inference works (`predict.py`)

1. Load the saved model and its feature columns.
2. For the target flight, build one synthetic row per day from today until
   departure ("what if the price were seen that day?").
3. Run those rows through the **same** `build_features()`, one-hot encode route,
   and `reindex` the columns to match training exactly.
4. Predict a price for each day.
5. The day with the lowest predicted price is the best time to book; if that is
   today, recommend BOOK NOW, otherwise WAIT. Returned as a dict (also served at
   `GET /predict/{origin}/{destination}`).

## Key design decisions

- **Shared feature module.** One source of truth for features, imported by both
  pipelines — the single most important guardrail in the ML layer.
- **Save feature columns with the model.** One-hot route columns depend on which
  routes existed at training time; saving the column list lets inference align.
- **Honest evaluation.** A held-out test set measures generalization, not
  memorization.
- **Reads from the warehouse only.** The ML layer consumes `price_quotes`; it
  never writes to it or touches ingestion.

## Running it

```bash
# Train the model on collected history (saves ml/models/model.joblib)
python -m ml.models.train

# Get a recommendation for a flight
python -m ml.models.predict

# Or via the API (with the FastAPI app running)
# GET http://127.0.0.1:8000/predict/YYC/LHR?departure_date=2026-09-01
```

## Status and known limitations

- **Built end to end:** data loading, feature engineering, training, inference,
  and the `/predict` API endpoint.
- **Not yet meaningful:** the model needs substantial real price history to
  learn anything useful. Early predictions are not trustworthy — this is a data
  maturity issue, not a code issue. Let the scheduler accumulate history first.
- **Simple feature set.** No historical/rolling features yet (e.g. price vs. the
  flight's own recent average). A natural next improvement, with care taken to
  avoid look-ahead leakage.
- **Full retrain each run.** `train.py` retrains from scratch; fine at this
  scale.
