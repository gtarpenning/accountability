"""
FastAPI application for serving Robinhood portfolio data.
Provides endpoints for historical portfolio data and YTD performance.
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import robin_stocks.robinhood as rh

from accountability.rh_api import (
    get_historical_portfolio_percentage,
    get_running_ytd_percentage,
)
from accountability.rh_types import (
    PercentageDate,
    FidelityType,
    SpanType,
    BoundsType,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Robinhood login when the application starts."""
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")
    if not password:
        raise HTTPException(
            status_code=500, detail="ROBINHOOD_PASSWORD environment variable not set"
        )
    rh.login(username, password)
    yield


app = FastAPI(title="Robinhood Portfolio API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/portfolio/historical/percentage", response_model=list[PercentageDate])
async def get_portfolio_history_percentage(
    fidelity: Optional[FidelityType] = "day",
    span: Optional[SpanType] = "week",
    bounds: Optional[BoundsType] = "regular",
) -> list[PercentageDate]:
    """Get historical portfolio data as percentage changes."""
    return get_historical_portfolio_percentage(
        fidelity=fidelity, span=span, bounds=bounds
    )


@app.get("/portfolio/ytd", response_model=list[PercentageDate])
async def get_ytd_performance() -> list[PercentageDate]:
    """Get the running YTD percentage change of the portfolio."""
    return get_running_ytd_percentage()


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
