# FlightSense

Flight price tracker and best-time-to-book predictor.

FlightSense records flight prices over time and lets you see a route's full
price history and the cheapest fare observed — the foundation for predicting
the best time to book.

## Tech stack

- **Python 3**
- **PostgreSQL** — stores the price history
- **SQLAlchemy 2.0** — database access (ORM)
- **FastAPI** — web API serving prices as JSON
- **python-dotenv** — loads configuration from a `.env` file

## Project structure

```
pipeline/
├── models/
│   ├── database.py     # DB connection: engine, SessionLocal, Base
│   ├── flight.py       # PriceQuote table definition (the schema)
│   └── init_db.py      # Creates the tables in PostgreSQL
├── collectors/
│   ├── save_quote.py   # Proof-of-concept: save one price, read it back
│   ├── collector.py    # Reusable record_quote() — saves any price
│   ├── flight_api.py   # Live price source — Amadeus Self-Service API
│   └── ingest.py       # Ingestion: fetch prices from the source → save them
├── queries.py          # Read prices back out: history + cheapest fare
└── scheduler.py        # Runs ingestion automatically on an interval

backend/
└── main.py             # FastAPI app — serves prices as JSON endpoints

ml/
├── data.py             # Load price history from PostgreSQL into a DataFrame
├── features/
│   └── build_features.py   # Turn raw price rows into model-ready features
└── models/
    ├── train.py        # Train the price model (XGBoost) + save it to disk
    └── predict.py      # Load the model + recommend BOOK NOW or WAIT
```

### What each script does

| Script | Purpose |
|--------|---------|
| `models/database.py` | The connection layer. Loads `DATABASE_URL` from `.env`, creates the SQLAlchemy `engine` (the connection to PostgreSQL), `SessionLocal` (a factory for database sessions), and `Base` (the parent class every table inherits from). Includes `test_connection()` to verify the database is reachable. |
| `models/flight.py` | Defines the `price_quotes` table as the `PriceQuote` model. One row = one price observed for a route at a point in time (origin, destination, departure date, price, currency, and the timestamp it was recorded). |
| `models/init_db.py` | Creates every defined table in PostgreSQL via `Base.metadata.create_all()`. Run once; safe to re-run. |
| `collectors/save_quote.py` | First working end-to-end test — opens a session, saves one hardcoded price, and reads it back. Proves the connect → write → read chain works. |
| `collectors/collector.py` | The reusable collector. `record_quote(origin, destination, departure_date, price, currency)` saves any price. This is the function the ingestion step calls, once per fare. |
| `collectors/flight_api.py` | The live price source. Authenticates to the **Amadeus Self-Service API** and returns the cheapest current fare for each tracked flight. Requires `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET` in `.env`. |
| `collectors/ingest.py` | The ingestion step — the "pull data in" stage. `fetch_prices()` gets current prices from the live source, and `ingest()` saves each via `record_quote()`. |
| `queries.py` | The read layer. `get_price_history()` returns a route's prices over time; `get_cheapest()` returns the lowest fare seen. These are the functions the FastAPI routes wrap. |
| `scheduler.py` | Runs `ingest()` automatically on a fixed interval (APScheduler), so prices collect unattended and history builds over time. Runs once on startup, then repeats. |
| `backend/main.py` | The FastAPI web app. Thin HTTP layer over `queries.py` — it does not touch the database directly, it calls the query functions and returns JSON. Exposes a health check plus price-history and cheapest-fare endpoints. |
| `ml/data.py` | Loads price history from PostgreSQL into a pandas DataFrame. The only ML file that talks to the database. `load_all_quotes()` (training) and `load_quotes_for_flight()` (inference). |
| `ml/features/build_features.py` | Feature engineering — turns raw price rows into numeric features (days-to-departure, calendar features, route). Shared by both training and prediction so features are built identically. |
| `ml/models/train.py` | Training pipeline. Loads data → builds features → trains an XGBoost regression model to predict price → evaluates on a held-out test set → saves the model (and its feature columns) to `model.joblib`. |
| `ml/models/predict.py` | Inference pipeline. Loads the saved model, predicts prices across the days left before departure, and recommends **BOOK NOW** or **WAIT**. Also served via the API's `/predict` endpoint. |

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the database connection**

   Create a `.env` file in the project root:

   ```
   DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
   ```

   Example (local PostgreSQL):

   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/flightsense
   ```

   For live price ingestion, also add your Amadeus API credentials (sign up
   free at https://developers.amadeus.com):

   ```
   AMADEUS_CLIENT_ID=your_api_key
   AMADEUS_CLIENT_SECRET=your_api_secret
   ```

3. **Verify the connection** (optional but recommended)

   ```bash
   python -m pipeline.models.database
   ```

   Expected output: `✅ Database connection successful.`

4. **Create the tables**

   ```bash
   python -m pipeline.models.init_db
   ```

   Expected output: `✅ Tables created (or already existed).`

## Usage

Ingest current prices into the database (uses a mock source for now — run it
a few times to build up price history):

```bash
python -m pipeline.collectors.ingest
```

Or run ingestion continuously on a schedule (collects now, then every interval;
Ctrl+C to stop):

```bash
python -m pipeline.scheduler
```

Read the price history and cheapest fare back out:

```bash
python -m pipeline.queries
```

> All commands are run from the project root so the `pipeline` package resolves.

### Run the API

```bash
uvicorn backend.main:app --reload
```

Then visit:

- `http://127.0.0.1:8000/docs` — interactive, auto-generated API docs
- `http://127.0.0.1:8000/prices/YYC/LHR?departure_date=2026-09-01` — price history for a flight
- `http://127.0.0.1:8000/prices/YYC/LHR/cheapest?departure_date=2026-09-01` — cheapest fare seen
- `http://127.0.0.1:8000/predict/YYC/LHR?departure_date=2026-09-01` — ML recommendation: book now or wait (requires a trained model)

### Train and use the model

Train the price model on the collected history (saves `ml/models/model.joblib`):

```bash
python -m ml.models.train
```

Get a book-now-or-wait recommendation for a flight:

```bash
python -m ml.models.predict
```

> The model is only as good as the data behind it. Let the scheduler collect
> real price history before trusting predictions.

## Documentation

- [Data Engineering](docs/data-engineering.md) — how prices flow from the
  Amadeus API into PostgreSQL and back out, the data model, and design decisions.
- [Machine Learning](docs/machine-learning.md) — how the model is trained and
  used to recommend when to book, the features, and the training/inference split.

## Roadmap

- [x] Database connection layer
- [x] `PriceQuote` schema and table creation
- [x] Reusable collector (`record_quote`)
- [x] Read layer (price history + cheapest fare)
- [x] FastAPI endpoints to serve prices as JSON
- [x] Ingestion pipeline (fetch → record)
- [x] Scheduled collection (APScheduler)
- [x] Live flight-price API source (Amadeus Self-Service)
- [x] Best-time-to-book prediction model (train + predict + `/predict` endpoint)
