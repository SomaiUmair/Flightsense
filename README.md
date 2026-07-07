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
│   └── ingest.py       # Ingestion: fetch prices from a source → save them
└── queries.py          # Read prices back out: history + cheapest fare

backend/
└── main.py             # FastAPI app — serves prices as JSON endpoints
```

### What each script does

| Script | Purpose |
|--------|---------|
| `models/database.py` | The connection layer. Loads `DATABASE_URL` from `.env`, creates the SQLAlchemy `engine` (the connection to PostgreSQL), `SessionLocal` (a factory for database sessions), and `Base` (the parent class every table inherits from). Includes `test_connection()` to verify the database is reachable. |
| `models/flight.py` | Defines the `price_quotes` table as the `PriceQuote` model. One row = one price observed for a route at a point in time (origin, destination, departure date, price, currency, and the timestamp it was recorded). |
| `models/init_db.py` | Creates every defined table in PostgreSQL via `Base.metadata.create_all()`. Run once; safe to re-run. |
| `collectors/save_quote.py` | First working end-to-end test — opens a session, saves one hardcoded price, and reads it back. Proves the connect → write → read chain works. |
| `collectors/collector.py` | The reusable collector. `record_quote(origin, destination, departure_date, price, currency)` saves any price. This is the function the ingestion step calls, once per fare. |
| `collectors/ingest.py` | The ingestion step — the "pull data in" stage. `fetch_prices()` gets current prices (currently a **mock** source), and `ingest()` saves each via `record_quote()`. To go live, replace only `fetch_prices()` with real flight-API calls. |
| `queries.py` | The read layer. `get_price_history()` returns a route's prices over time; `get_cheapest()` returns the lowest fare seen. These are the functions the FastAPI routes wrap. |
| `backend/main.py` | The FastAPI web app. Thin HTTP layer over `queries.py` — it does not touch the database directly, it calls the query functions and returns JSON. Exposes a health check plus price-history and cheapest-fare endpoints. |

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

## Roadmap

- [x] Database connection layer
- [x] `PriceQuote` schema and table creation
- [x] Reusable collector (`record_quote`)
- [x] Read layer (price history + cheapest fare)
- [x] FastAPI endpoints to serve prices as JSON
- [x] Ingestion pipeline (fetch → record) with a mock source
- [ ] Swap the mock source for a live flight-price API
- [ ] Scheduled collection (APScheduler)
- [ ] Best-time-to-book prediction model
