# FlightSense: Data Engineering

This document explains the data engineering side of FlightSense: how flight
prices flow from an external API into PostgreSQL, and how they are read back
out. It is the collect-and-store foundation the API and ML layers build on.

## Purpose

FlightSense tracks flight prices over time so it can predict the best time to
book. The data engineering layer has one job: reliably capture prices and
store their history. One stored row is one price observed for one route on one
date, at one moment in time. The same flight is recorded repeatedly, so its
price history is simply all of its rows ordered by time.

## Architecture at a glance

```
 Travelpayouts          pipeline (data engineering)             PostgreSQL
+------------+  fetch  +------------+  record  +------------+  store  +--------------+
| cached     | ------> | flight_api | -------> | ingest /   | ------> | price_quotes |
| fares      |         |  .py       |          | collector  |         |    table     |
+------------+         +------------+          +------------+         +------+-------+
                             ^                                               | read
                       +-----+------+  every 30 min                  +------v-------+
                       | scheduler  | -------------------------------|  queries.py  |
                       |  .py       |                                +--------------+
                       +------------+
```

Data flow: the scheduler triggers ingestion on an interval. Ingestion asks the
Travelpayouts source for current prices. Each price is saved to
`price_quotes`. The query layer reads that history back out, and the FastAPI
app serves it.

## Components

| File | Role |
|------|------|
| `pipeline/models/database.py` | Connection layer. Loads `DATABASE_URL` from `.env`, creates the SQLAlchemy `engine` (pooled connection), `SessionLocal` (session factory), and `Base` (parent class for all tables). Includes `test_connection()`. |
| `pipeline/models/flight.py` | The schema. Defines the `price_quotes` table via the `PriceQuote` model. |
| `pipeline/models/init_db.py` | Creates the tables in PostgreSQL. Run once. |
| `pipeline/collectors/flight_api.py` | The price source. Queries Travelpayouts and returns recently found one-way fares for each tracked route, cheapest per departure date. |
| `pipeline/collectors/collector.py` | The saver. `record_quote(...)` writes one price to the database. |
| `pipeline/collectors/ingest.py` | The ingestion step. `fetch_prices()` gets prices from the source and `ingest()` saves each one. |
| `pipeline/scheduler.py` | Runs `ingest()` automatically on an interval (APScheduler), so history builds unattended. |
| `pipeline/queries.py` | The read layer. `get_price_history()` and `get_cheapest()` read prices back out. |

## The data model: price_quotes

| Column | Type | Notes |
|--------|------|-------|
| `id` | integer, PK | Auto-incrementing unique row id. |
| `origin` | varchar(3) | City code, indexed. |
| `destination` | varchar(3) | City code, indexed. |
| `departure_date` | date | The flight's date, indexed. |
| `price` | numeric(10,2) | Exact decimal, not float. Money must not round. |
| `currency` | varchar(3) | ISO code, for example USD. |
| `observed_at` | timestamptz | When the price was recorded. Stamped by the database, indexed. |

A composite index on (origin, destination, departure_date) supports the most
common query: the price history of one specific flight over time.

## How the data flows, step by step

1. Trigger: `scheduler.py` fires `ingest()` immediately on startup, then every
   30 minutes.
2. Fetch: `ingest.fetch_prices()` calls `flight_api.get_live_prices()`, which
   queries Travelpayouts (token auth) for each tracked route and returns the
   cheapest recently found fare per departure date as plain dicts. Routes use
   city codes (YTO, LON, PAR) because that is how the API keys its data.
3. Save: `ingest()` loops over the fetched prices and calls
   `collector.record_quote()` for each. That opens a session, inserts a
   `PriceQuote`, commits, and returns the saved row.
4. Store: PostgreSQL stamps `id` and `observed_at`. The row joins the flight's
   growing price history.
5. Read: `queries.py` reads the history back, and the FastAPI app in
   `backend/` serves it as JSON.

## Key design decisions

- Source separated from saver. `flight_api.py` (where data comes from) is
  isolated from `collector.py` (how it is stored). This seam has paid off
  twice: swapping the mock for the live Amadeus API touched only
  `fetch_prices()`, and when Amadeus shut down its self-service portal in July
  2026, swapping in Travelpayouts touched only this one module. Nothing
  downstream moved either time.
- One connection, many sessions. The engine is created once and shared. Each
  unit of work gets a short-lived session. Standard SQLAlchemy practice.
- Numeric, never float, for money. Floats introduce rounding errors and prices
  must be exact.
- Timestamp every observation. Storing `observed_at` on every row is what
  makes this a price tracker (history) rather than a static price list.
- Fail fast on config. A missing `DATABASE_URL` or Travelpayouts token raises
  a clear error at startup rather than failing in a confusing way later.

## Configuration

In `.env` at the project root:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
TRAVELPAYOUTS_TOKEN=your_api_token
```

The token comes from a free account at https://www.travelpayouts.com.

## Running it

```bash
# 1. Verify the database connection (optional)
python -m pipeline.models.database

# 2. Create the table (once)
python -m pipeline.models.init_db

# 3. Ingest once, on demand
python -m pipeline.collectors.ingest

# 4. Or run ingestion continuously on a schedule
python -m pipeline.scheduler

# 5. Read prices back out
python -m pipeline.queries
```

## Status and known limitations

- Built: connection, schema, table creation, live Travelpayouts source,
  ingestion, scheduling, and the read layer. The pipeline runs end to end.
- Cached prices. Travelpayouts serves fares cached from recent traveller
  searches, not live availability. A route or date with thin search traffic
  can return nothing on a given run. Good for trend history, not bookable
  fares.
- The scheduler runs in the foreground. Unattended production use would run it
  as a managed service (cron or a cloud scheduler), not a local process.
- No dedupe or backfill. Every run records a new observation. The API does not
  provide historical prices, so there is no backfill.

## What comes next

The machine learning layer (`ml/`) reads the accumulated `price_quotes`
history to predict the best time to book. It is documented separately in
[Machine Learning](machine-learning.md).
