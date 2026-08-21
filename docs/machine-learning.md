# FlightSense: Machine Learning

This document explains the machine learning layer: how FlightSense learns from
stored price history and turns it into a book-now-or-wait recommendation. It
reads from the same PostgreSQL database the data pipeline fills. It does not
touch ingestion.

## Goal

Given a flight (route plus departure date), recommend whether to book now or
wait for a better price. The model predicts the fare, then compares the
predicted price across the days left before departure.

## Problem framing

- Type: regression. The model predicts a number (the price), not a yes/no.
- Target (y): `price`.
- Features (X): signals derived from each price observation. The strongest is
  `days_to_departure`, plus calendar features and the route.

## The two pipelines

Machine learning here is two separate flows that run at different times:

```
TRAINING  (offline, occasional)   load -> features -> train -> SAVE model file
INFERENCE (on demand)             build features -> LOAD model file -> predict
```

They share one thing that must be identical in both: feature engineering. If
training and inference build features differently, predictions are garbage.
That shared logic lives in `ml/features/build_features.py`, and both pipelines
import it. The saved model file (`ml/models/model.joblib`) is the handoff
between the two.

## Components

| File | Role |
|------|------|
| `ml/data.py` | Loads price history from PostgreSQL into a pandas DataFrame. The only ML file that touches the database. |
| `ml/features/build_features.py` | Turns raw price rows into model features. Shared by training and inference. |
| `ml/models/train.py` | Training pipeline: load, build features, time-based train/test split, fit XGBoost, evaluate, save the model and feature columns. |
| `ml/models/predict.py` | Inference pipeline: load the model, predict prices across the remaining days, recommend BOOK NOW or WAIT. |
| `backend/main.py` (`/predict`) | Serves the recommendation as JSON over HTTP. |

## Features

Built in `build_features()` from each raw price row:

| Feature | Meaning |
|---------|---------|
| `days_to_departure` | Days between when the price was observed and the flight. The strongest signal. |
| `observed_dow`, `observed_month` | When the price was seen (weekly and seasonal patterns). |
| `departure_dow`, `departure_month` | When the flight departs. |
| `route` | Origin-destination label (for example YTO-PAR), one-hot encoded before training. |

## How training works (train.py)

1. Load all history and build features.
2. Guard: if there are very few rows, warn. A model trained on little data is
   meaningless.
3. Split into train and test by time: the test set is the newest 20% of
   observations, so the score measures real forecasting on data newer than
   anything the model trained on. A random split would leak future patterns
   into training and flatter the score.
4. Fit an XGBRegressor.
5. Evaluate with mean absolute error (average dollars off) on the test set.
6. Save the model and its feature columns to `model.joblib`. The column list
   lets inference reproduce the exact same input shape.

## How inference works (predict.py)

1. Load the saved model and its feature columns.
2. For the target flight, build one synthetic row per day from today until
   departure, as if the price were observed on each of those days.
3. Run those rows through the same `build_features()`, one-hot encode the
   route, and reindex the columns to match training exactly.
4. Predict a price for each day.
5. The day with the lowest predicted price is the best time to book. If that
   day is today, recommend BOOK NOW. Otherwise recommend WAIT. Returned as a
   dict and served at `GET /predict/{origin}/{destination}`.

## Key design decisions

- Shared feature module. One source of truth for features, imported by both
  pipelines. This is the most important guardrail in the ML layer.
- Feature columns saved with the model. One-hot route columns depend on which
  routes existed at training time. Saving the column list lets inference
  align.
- Time-based evaluation. The test set is strictly newer than the training
  data, so the reported error measures forecasting, not interpolation.
- Reads from the database only. The ML layer consumes `price_quotes`. It never
  writes to it and never touches ingestion.

## Running it

```bash
# Train the model on collected history (saves ml/models/model.joblib)
python -m ml.models.train

# Get a recommendation for a flight
python -m ml.models.predict

# Or via the API (with the FastAPI app running)
# GET http://127.0.0.1:8000/predict/YTO/PAR?departure_date=2026-09-20
```

## Status and known limitations

- Built end to end: data loading, feature engineering, training, inference,
  and the `/predict` API endpoint.
- Predictions improve with history. The model learns from the same flight
  being observed at different prices on different days, so accuracy grows as
  the scheduler collects more data.
- The model smooths sudden fare spikes. When a route jumps overnight, the
  prediction lags toward the historical average for a few days.
- Simple feature set. No rolling or historical features yet (for example,
  price versus the flight's own recent average). A natural next improvement,
  with care to avoid look-ahead leakage.
- Full retrain each run. `train.py` retrains from scratch, which is fine at
  this scale.
