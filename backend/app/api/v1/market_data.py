"""FastAPI route for retrieving validated daily historical market data and technical indicators."""

from typing import Literal
from fastapi import APIRouter, HTTPException, Path, Query, status

from app.schemas.market_data import MarketDataResponse, ValidationStatus
from app.services.market_data_service import MarketDataService

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get(
    "/{ticker}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Daily Historical Market Data & Indicators",
    description=(
        "Fetch, validate, and compute technical indicators (Daily Return, 20-SMA, 50-SMA, "
        "and 20-session Annualized Volatility) for an equity ticker symbol (defaults to NSE .NS suffix). "
        "Returns explicit audit and validation flags without database dependency."
    ),
)
async def get_market_data(
    ticker: str = Path(
        ...,
        description="Stock ticker symbol (e.g. 'TCS', 'TCS.NS', 'INFY', 'RELIANCE')",
        min_length=1,
        max_length=30,
    ),
    period: Literal["1mo", "3mo", "6mo", "1y", "2y", "5y"] = Query(
        default="6mo",
        description="Historical data lookback timeframe (standard daily bars)",
    ),
) -> MarketDataResponse:
    """Retrieve validated historical daily market data, audit results, and deterministic indicators."""
    response = await MarketDataService.get_daily_market_data(ticker=ticker, period=period)

    # If the response is marked as invalid due to an error, we still return HTTP 200 with validation.status='invalid'
    # so clients receive the full diagnostic issue list, or 404 if symbol is truly not found.
    # Check if there is an EMPTY_DATASET error indicating symbol could not be found
    empty_dataset_error = any(
        issue.code == "EMPTY_DATASET" for issue in response.validation.issues
    )
    if empty_dataset_error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market data found for ticker symbol '{ticker}' (resolved as '{response.provider_ticker}').",
        )

    return response
