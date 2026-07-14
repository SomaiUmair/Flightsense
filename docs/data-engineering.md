# FlightSense — Data Engineering

This document explains the data engineering side of FlightSense: how flight
prices flow from an external API into PostgreSQL, and how they are read back
out. It's the "collect and store" foundation the API and ML layers build on.

## Purpose

FlightSense tracks flight prices over time so it can eventually predict the
best time to book. The data engineering layer's single job is to **reliably
capture prices and store their history**. One stored row = one price observed
for one route on one date, at one moment in time. The same flight is recorded
repeatedly, so its price history is simply all its rows ordered by time.

## Architecture at a glance

```
 Travelpayouts          pipeline (data engineering)              PostgreSQL
┌────────────┐   fetch  ┌───────────┐   record   ┌────────────┐  store  ┌──────────────┐
│ cached     │────────► │ flight_api│──────────► │ ingest /   │───────► │ price_quotes │
│ fares      │          │  .py      │            │ collector  │         │   table      │
└────────────┘          └───────────┘            └────────────┘         └──────┬───────┘
                             ▲                                                  │ read
                        ┌────┴─────┐  every 30 min                       ┌──────▼───────┐
                        │scheduler │─────────────────────────────────────│  queries.py  │
                        │  .py     │                                      └──────────────┘
                        └──────────┘
```

**Data flow:** the scheduler triggers ingestion on an interval → ingestion asks
the Travelpayouts source for current prices → each price is saved to `price_quotes` →
the query layer reads that history back out (and the FastAPI app serves it).

## Components

| File | Role |
|------|------|
| `pipeline/models/database.py` | Connection layer. Loads `DATABASE_URL` from `.env`; creates the SQLAlchemy `engine` (pooled connection to PostgreSQL), `SessionLocal` (session factory), and `Base` (parent class for all tables). Includes `test_connection()`. |
| `pipeline/models/flight.py` | The schema. Defines the `price_quotes` table via the `PriceQuote` model. |
| `pipeline/models/init_db.py` | Creates the tables in PostgreSQL (`Base.metadata.create_all`). Run once. |
| `pipeline/collectors/flight_api.py` | Live price **source**. Queries Travelpayouts and returns recently-found one-way fares for each tracked route — cheapest per departure date. |
| `pipeline/collectors/collector.py` | The **saver**. `record_quote(...)` writes one price to the database. |
| `pipeline/collectors/ingest.py` | The **ingestion** step. `fetch_prices()` gets prices from the source; `ingest()` saves each via `record_quote()`. |
| `pipeline/scheduler.py` | Runs `ingest()` automatically on an interval (APScheduler), so history builds unattended. |
| `pipeline/queries.py` | The **read** layer. `get_price_history()` and `get_cheapest()` read prices back out. |

## The data model: `price_quotes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | integer, PK | Auto-incrementing unique row id. |
| `origin` | varchar(3) | IATA airport code, indexed. |
| `destination` | varchar(3) | IATA airport code, indexed. |
| `departure_date` | date | The flight's date, indexed. |
| `price` | numeric(10,2) | Exact decimal (not float) — money must not round. |
| `currency` | varchar(3) | ISO code, e.g. USD. |
| `observed_at` | timestamptz | When we recorded the price; DB-stamped default, indexed. |

A composite index on `(origin, destination, departure_date)` supports the most
common query: the price history for one specific flight over time.

## How the data flows, step by step

1. **Trigger** — `scheduler.py` fires `ingest()` immediately on startup, then
   every 30 minutes (configurable; production would use hours).
2. **Fetch** — `ingest.fetch_prices()` delegates to `flight_api.get_live_prices()`,
   which queries Travelpayouts (token auth) for each tracked route and returns
   the cheapest recently-found fare per departure date as plain dicts. Routes
   use city codes (YTO, LON, PAR) because that is how the API keys its data.
3. **Save** — `ingest()` loops the fetched prices and calls
   `collector.record_quote()` for each, which opens a session, inserts a
   `PriceQuote`, commits, and returns the saved row.
4. **Store** — PostgreSQL stamps `id` and `observed_at`; the row joins the
   flight's growing price history.
5. **Read** — `queries.py` reads that history back (`get_price_history`,
   `get_cheapest`); the FastAPI app in `backend/` serves it as JSON.

## Key design decisions

- **Source separated from saver.** `flight_api.py` (where data comes from) is
  isolated from `collector.py` (how it's stored). This seam has paid off twice:
  swapping the mock for the live Amadeus API touched only `fetch_prices()`, and
  when Amadeus decommissioned its self-service portal (July 2026), swapping in
  Travelpayouts touched only this one module. Nothing downstream moved either
  time.
- **One connection, many sessions.** The `engine` is created once and shared;
  each unit of work gets a short-lived session. Standard SQLAlchemy practice.
- **`Numeric`, never `Float`, for money.** Floats introduce rounding errors;
  prices must be exact.
- **Timestamp every observation.** Storing `observed_at` on every row is what
  makes this a price *tracker* (history) rather than a static price list.
- **Fail fast on config.** Missing `DATABASE_URL` or the Travelpayouts token
  raises a clear error at startup rather than failing obscurely later.

## Configuration

In `.env` (project root):

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

- **Built:** connection, schema, table creation, live Travelpayouts source,
  ingestion, scheduling, and the read layer. The pipeline runs end to end.
- **Cached prices.** Travelpayouts serves fares cached from recent traveller
  searches, not live availability — a route/date with thin search traffic can
  return nothing on a given run. Fine for trend history; not bookable fares.
- **Scheduler runs in the foreground.** For unattended production use it would
  run as a managed service (cron / systemd / a cloud scheduler), not a local
  process.
- **No dedupe or backfill.** Every run records a new observation; there is no
  historical backfill of past prices (the API doesn't provide it).

## What's next (not part of data engineering)

The machine learning layer (`ml/`) reads the accumulated `price_quotes` history
to predict the best time to book. It is built and documented separately in
[Machine Learning](machine-learning.md).
