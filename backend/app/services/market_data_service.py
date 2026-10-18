"""Market data retrieval service using yfinance for daily historical equity data."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
import pandas as pd
import yfinance as yf

from app.core.logging import get_logger
from app.schemas.market_data import (
    CompanyInfo,
    DailyBar,
    MarketDataResponse,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from app.services.indicator_service import TechnicalIndicatorCalculator
from app.services.market_data_validator import MarketDataValidator

logger = get_logger(__name__)

# Dedicated thread pool for non-blocking execution of blocking yfinance I/O calls
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


class MarketDataService:
    """Orchestrates daily historical equity data fetching, integrity auditing, and indicator computation."""

    DEFAULT_TIMEOUT_SECONDS: float = 12.0

    @staticmethod
    def resolve_symbol(ticker: str) -> str:
        """Sanitize and normalize symbol for Yahoo Finance NSE equity resolution.

        Examples:
            'TCS' -> 'TCS.NS'
            'TCS.NS' -> 'TCS.NS'
            'INFY' -> 'INFY.NS'
            'AAPL' -> 'AAPL'
        """
        clean = ticker.strip().upper()
        # Remove any unwanted characters
        clean = re.sub(r"[^A-Z0-9\.\^=_-]", "", clean)

        # If ticker does not contain an exchange suffix (e.g. .NS, .BO, .L) and is standard ticker:
        # Default typical Indian symbols to .NS if not specified, or keep as requested if contains '.'
        if "." not in clean and "=" not in clean and "^" not in clean:
            # By requirement, default to NSE (.NS) for standard equity tickers
            return f"{clean}.NS"
        return clean

    @classmethod
    async def get_daily_market_data(
        cls,
        ticker: str,
        period: str = "6mo",
    ) -> MarketDataResponse:
        """Fetch, validate, and compute indicators for daily historical price data.

        Args:
            ticker: Stock symbol (e.g. 'TCS' or 'TCS.NS').
            period: Historical timeframe ('1mo', '3mo', '6mo', '1y', '2y', '5y', 'max').

        Returns:
            MarketDataResponse: Structured, validated response with audit details and indicators.
        """
        requested_ticker = ticker.strip().upper()
        provider_ticker = cls.resolve_symbol(requested_ticker)
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(f"Fetching daily market data for {provider_ticker} (period: {period})")

        # Execute blocking yfinance download in worker thread with timeout
        loop = asyncio.get_running_loop()
        try:
            raw_df, info_dict = await asyncio.wait_for(
                loop.run_in_executor(
                    _EXECUTOR,
                    cls._fetch_yfinance_data_sync,
                    provider_ticker,
                    period,
                ),
                timeout=cls.DEFAULT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while retrieving market data for {provider_ticker}")
            return cls._build_timeout_response(requested_ticker, provider_ticker, retrieval_timestamp)
        except Exception as exc:
            logger.error(f"Error fetching data from provider for {provider_ticker}: {exc}")
            return cls._build_error_response(
                requested_ticker,
                provider_ticker,
                retrieval_timestamp,
                f"Market data provider error: {str(exc)}",
            )

        # 2. Extract company info if available
        company_info = cls._extract_company_info(info_dict)

        # 3. Validate OHLCV DataFrame
        validation_result, clean_df = MarketDataValidator.validate_ohlcv_dataframe(raw_df, provider_ticker)

        # If dataset was fundamentally invalid (e.g. empty or corrupted)
        if validation_result.status == ValidationStatus.INVALID or clean_df.empty:
            return MarketDataResponse(
                requested_ticker=requested_ticker,
                provider_ticker=provider_ticker,
                provider="Yahoo Finance (via yfinance daily historical)",
                is_live_price=False,
                retrieval_timestamp=retrieval_timestamp,
                company=company_info,
                validation=validation_result,
                price_history=[],
                indicator_series=[],
            )

        # 4. Compute deterministic technical indicators
        indicator_series, indicator_summary = TechnicalIndicatorCalculator.calculate(clean_df)

        # 5. Build chronological DailyBar records
        price_history: List[DailyBar] = []
        for idx in clean_df.index:
            row = clean_df.loc[idx]
            price_history.append(
                DailyBar(
                    date=idx.strftime("%Y-%m-%d"),
                    open=round(float(row["Open"]), 2),
                    high=round(float(row["High"]), 2),
                    low=round(float(row["Low"]), 2),
                    close=round(float(row["Close"]), 2),
                    adj_close=round(float(row["Adj Close"]), 2) if "Adj Close" in clean_df.columns and pd.notna(row.get("Adj Close")) else None,
                    volume=int(row.get("Volume", 0)),
                )
            )

        latest_date = clean_df.index[-1].strftime("%Y-%m-%d")
        latest_close = round(float(clean_df["Close"].iloc[-1]), 2)

        return MarketDataResponse(
            requested_ticker=requested_ticker,
            provider_ticker=provider_ticker,
            provider="Yahoo Finance (via yfinance daily historical)",
            is_live_price=False,
            price_series_convention="raw_close",
            retrieval_timestamp=retrieval_timestamp,
            latest_trading_date=latest_date,
            latest_close=latest_close,
            company=company_info,
            validation=validation_result,
            indicators_summary=indicator_summary,
            price_history=price_history,
            indicator_series=indicator_series,
        )

    @classmethod
    def _fetch_yfinance_data_sync(cls, provider_ticker: str, period: str) -> Tuple[pd.DataFrame, dict]:
        """Synchronous worker function to fetch yfinance history and fast_info."""
        ticker_obj = yf.Ticker(provider_ticker)
        # Fetch daily bars without forward filling or fabricated data
        df = ticker_obj.history(period=period, interval="1d", auto_adjust=False)

        info_dict = {}
        try:
            # Use fast_info when possible for speed and lower rate-limiting impact
            if hasattr(ticker_obj, "fast_info") and ticker_obj.fast_info:
                info_dict = {
                    "currency": getattr(ticker_obj.fast_info, "currency", None),
                    "exchange": getattr(ticker_obj.fast_info, "exchange", None),
                }
            # Fallback to info metadata if present and fast
            if hasattr(ticker_obj, "info") and isinstance(ticker_obj.info, dict):
                info_dict.update({
                    "name": ticker_obj.info.get("longName") or ticker_obj.info.get("shortName"),
                    "sector": ticker_obj.info.get("sector"),
                    "industry": ticker_obj.info.get("industry"),
                    "currency": ticker_obj.info.get("currency") or info_dict.get("currency"),
                    "exchange": ticker_obj.info.get("exchange") or info_dict.get("exchange"),
                })
        except Exception as e:
            logger.debug(f"Could not load extended company info for {provider_ticker}: {e}")

        return df, info_dict

    @staticmethod
    def _extract_company_info(info_dict: dict) -> CompanyInfo:
        return CompanyInfo(
            name=info_dict.get("name"),
            currency=info_dict.get("currency"),
            exchange=info_dict.get("exchange"),
            sector=info_dict.get("sector"),
            industry=info_dict.get("industry"),
        )

    @staticmethod
    def _build_timeout_response(requested: str, provider: str, ts: str) -> MarketDataResponse:
        return MarketDataResponse(
            requested_ticker=requested,
            provider_ticker=provider,
            provider="Yahoo Finance (via yfinance daily historical)",
            is_live_price=False,
            retrieval_timestamp=ts,
            validation=ValidationResult(
                status=ValidationStatus.INVALID,
                total_records=0,
                issues=[
                    ValidationIssue(
                        code="PROVIDER_TIMEOUT",
                        message="Upstream market data provider timed out. Please retry in a few seconds.",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
                warnings_count=0,
                errors_count=1,
            ),
            price_history=[],
            indicator_series=[],
        )

    @staticmethod
    def _build_error_response(requested: str, provider: str, ts: str, error_msg: str) -> MarketDataResponse:
        return MarketDataResponse(
            requested_ticker=requested,
            provider_ticker=provider,
            provider="Yahoo Finance (via yfinance daily historical)",
            is_live_price=False,
            retrieval_timestamp=ts,
            validation=ValidationResult(
                status=ValidationStatus.INVALID,
                total_records=0,
                issues=[
                    ValidationIssue(
                        code="PROVIDER_FETCH_ERROR",
                        message=error_msg,
                        severity=ValidationSeverity.ERROR,
                    )
                ],
                warnings_count=0,
                errors_count=1,
            ),
            price_history=[],
            indicator_series=[],
        )
