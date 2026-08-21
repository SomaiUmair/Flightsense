# FlightSense

FlightSense is a flight price tracker and best-time-to-book predictor. It
collects fares from the Travelpayouts API on a schedule, stores their history
in PostgreSQL, and serves price history plus a book-now-or-wait recommendation
through a FastAPI backend. It currently tracks 46 routes out of Canadian
cities.

## Tech stack

- Python 3 and FastAPI (web API)
- PostgreSQL and SQLAlchemy 2.0 (storage)
- APScheduler (scheduled ingestion)
- Travelpayouts Data API (fare data)
- scikit-learn and XGBoost (price model)

## Architecture

```
              +------------ scheduler (APScheduler) ------------+
              |                                                 |
              v                                                 |
Travelpayouts --> ingest --> PostgreSQL --> queries --> FastAPI --> client
                                |
                                +--> ml: data -> features -> train -> predict
```

- pipeline/ holds ingestion, storage, scheduling, and read queries
- backend/ holds the FastAPI app that exposes the endpoints
- ml/ holds feature engineering, model training, and prediction

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (then edit .env with real values)
cp .env.example .env

# 3. Create the database tables
python -m pipeline.models.init_db

# 4. Ingest prices (repeat, or run the scheduler to automate)
python -m pipeline.collectors.ingest

# 5. Run the API
uvicorn backend.main:app --reload
```

Requires a PostgreSQL instance (a free cloud one such as Neon works) and a
free Travelpayouts API token (https://www.travelpayouts.com), both set in
`.env`.

## API

Interactive docs at `/docs`. Three endpoints:

`GET /prices/{origin}/{destination}?departure_date=YYYY-MM-DD` returns the
full price history:

```json
[
  {
    "id": 12, "origin": "YYC", "destination": "LON",
    "departure_date": "2026-09-01", "price": 899.99,
    "currency": "USD", "observed_at": "2026-07-08T14:30:00Z"
  }
]
```

`GET /prices/{origin}/{destination}/cheapest?departure_date=YYYY-MM-DD`
returns the lowest fare recorded:

```json
{
  "id": 8, "origin": "YYC", "destination": "LON",
  "departure_date": "2026-09-01", "price": 812.50,
  "currency": "USD", "observed_at": "2026-07-05T09:00:00Z"
}
```

`GET /predict/{origin}/{destination}?departure_date=YYYY-MM-DD` returns the
book-now-or-wait recommendation:

```json
{
  "route": "YYC-LON", "departure_date": "2026-09-01",
  "predicted_price_today": 899.0, "cheapest_predicted_price": 812.34,
  "best_day_to_book": "2026-08-10", "recommendation": "WAIT"
}
```

## Documentation

- [Data Engineering](docs/data-engineering.md): ingestion, storage, and the data model
- [Machine Learning](docs/machine-learning.md): features, training, and prediction
