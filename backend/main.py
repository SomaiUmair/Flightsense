"""FastAPI application for FlightSense.

This is the web layer. It turns the read functions in pipeline/queries.py into
HTTP endpoints you can hit from a browser or another app. The API is thin on
purpose: it does NOT talk to the database directly -- it calls the query
functions and returns their results as JSON. All the data logic stays in one
place (pipeline/), the API just exposes it.

Run it with:
    uvicorn backend.main:app --reload

Then open http://127.0.0.1:8000/docs for interactive, auto-generated docs.
"""

from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from pipeline.queries import get_cheapest, get_price_history

# The application object. FastAPI/uvicorn look for this `app` variable.
# title/description show up in the auto-generated docs at /docs.
app = FastAPI(
    title="FlightSense",
    description="Flight price tracker and best-time-to-book predictor.",
)


class PriceQuoteOut(BaseModel):
    """The shape of a price returned to API clients.

    A PriceQuote is a SQLAlchemy object; the web can't send that directly. This
    Pydantic model defines exactly which fields we expose and their types, then
    serializes them to JSON. from_attributes=True lets it read straight from a
    PriceQuote object's attributes.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    origin: str
    destination: str
    departure_date: date
    price: float
    currency: str
    observed_at: datetime


@app.get("/")
def root() -> dict:
    """Health check — confirms the API is up."""
    return {"status": "ok", "service": "FlightSense"}


@app.get("/prices/{origin}/{destination}", response_model=list[PriceQuoteOut])
def price_history(origin: str, destination: str, departure_date: date):
    """Full price history for one flight, oldest observation first.

    `departure_date` comes from the query string, e.g.
        /prices/YYC/LHR?departure_date=2026-09-01
    FastAPI parses it into a real date and rejects bad formats automatically.
    """
    # Uppercase the codes so /prices/yyc/lhr works the same as /prices/YYC/LHR.
    return get_price_history(origin.upper(), destination.upper(), departure_date)


@app.get(
    "/prices/{origin}/{destination}/cheapest", response_model=PriceQuoteOut
)
def cheapest(origin: str, destination: str, departure_date: date):
    """The single lowest fare ever recorded for one flight."""
    result = get_cheapest(origin.upper(), destination.upper(), departure_date)
    # No rows for this flight -> return a proper 404 instead of null.
    if result is None:
        raise HTTPException(status_code=404, detail="No prices recorded for that flight.")
    return result
