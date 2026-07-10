"""FastAPI application for FlightSense.

Thin HTTP layer over the pipeline query and ML functions; returns JSON. Run with
`uvicorn backend.main:app --reload` (interactive docs at /docs).
"""

from datetime import date, datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from pipeline.queries import get_cheapest, get_price_history

app = FastAPI(
    title="FlightSense",
    description="Flight price tracker and best-time-to-book predictor.",
)


class PriceQuoteOut(BaseModel):
    """JSON shape for a price returned to clients.

    from_attributes=True lets FastAPI read fields straight off the SQLAlchemy row.
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
    """Health check."""
    return {"status": "ok", "service": "FlightSense"}


@app.get("/prices/{origin}/{destination}", response_model=list[PriceQuoteOut])
def price_history(origin: str, destination: str, departure_date: date):
    """Full price history for one flight, oldest first."""
    # Uppercase so /prices/yyc/lhr matches the stored codes.
    return get_price_history(origin.upper(), destination.upper(), departure_date)


@app.get(
    "/prices/{origin}/{destination}/cheapest", response_model=PriceQuoteOut
)
def cheapest(origin: str, destination: str, departure_date: date):
    """Lowest fare ever recorded for one flight."""
    result = get_cheapest(origin.upper(), destination.upper(), departure_date)
    if result is None:
        raise HTTPException(status_code=404, detail="No prices recorded for that flight.")
    return result


@app.get("/predict/{origin}/{destination}")
def predict(origin: str, destination: str, departure_date: date):
    """Recommend BOOK NOW or WAIT using the trained model."""
    # Imported here, not at module top: this pulls in the whole ML stack
    # (xgboost/sklearn/pandas), which takes far too long at startup on
    # AV-scanned machines. Lazy-loading keeps API startup fast; the first
    # /predict call pays the import cost instead.
    from ml.models.predict import recommend

    try:
        return recommend(origin.upper(), destination.upper(), departure_date)
    except ValueError as error:
        # e.g. departure_date in the past.
        raise HTTPException(status_code=400, detail=str(error))
    except RuntimeError as error:
        # Model file doesn't exist yet — surface as "service not ready".
        raise HTTPException(status_code=503, detail=str(error))
