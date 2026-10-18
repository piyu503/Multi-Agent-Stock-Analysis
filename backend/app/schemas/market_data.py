"""Market data Pydantic schemas for historical daily OHLCV and technical indicators."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue(BaseModel):
    code: str = Field(..., description="Machine-readable issue code")
    message: str = Field(..., description="Human-readable explanation")
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.WARNING,
        description="Severity level of the validation issue",
    )
    details: Optional[dict] = Field(default=None, description="Diagnostic details and affected dates")


class ValidationStatus(str, Enum):
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"


class ValidationResult(BaseModel):
    status: ValidationStatus = Field(..., description="Overall dataset validation status")
    total_records: int = Field(..., description="Count of historical daily records validated and retained")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of detected anomalies or warnings")
    warnings_count: int = Field(default=0, description="Total count of non-critical warnings")
    errors_count: int = Field(default=0, description="Total count of validation-breaking errors")


class DailyBar(BaseModel):
    date: str = Field(..., description="Trading session calendar date in YYYY-MM-DD format (exchange local date)")
    open: float = Field(..., description="Opening price for session (raw unadjusted)")
    high: float = Field(..., description="Session highest price (raw unadjusted)")
    low: float = Field(..., description="Session lowest price (raw unadjusted)")
    close: float = Field(..., description="Session closing price (raw unadjusted)")
    adj_close: Optional[float] = Field(None, description="Closing price adjusted for splits and dividends")
    volume: int = Field(..., description="Trading volume during session")


class IndicatorSeries(BaseModel):
    date: str = Field(..., description="Trading session date in YYYY-MM-DD format")
    daily_return_pct: Optional[float] = Field(
        None, description="Daily percentage price change ((close_t / close_{t-1}) - 1) * 100 on raw Close"
    )
    sma_20: Optional[float] = Field(
        None, description="20-trading-session simple moving average of raw close price"
    )
    sma_50: Optional[float] = Field(
        None, description="50-trading-session simple moving average of raw close price"
    )
    volatility_20_annualized_pct: Optional[float] = Field(
        None,
        description=(
            "20-session annualized historical volatility percentage of daily returns "
            "(std(daily_returns_pct, ddof=1) * sqrt(252)). Requires 20 daily returns (21 price sessions)."
        ),
    )
    rsi_14: Optional[float] = Field(
        None, description="14-session Relative Strength Index (Wilder's RSI). Requires at least 15 price bars."
    )
    volume_sma_20: Optional[float] = Field(
        None, description="20-session simple moving average of traded volume"
    )
    relative_volume: Optional[float] = Field(
        None, description="Ratio of session volume to 20-session average volume (Volume / SMA20_Volume)"
    )


class IndicatorSummary(BaseModel):
    latest_daily_return_pct: Optional[float] = None
    latest_sma_20: Optional[float] = None
    latest_sma_50: Optional[float] = None
    latest_volatility_20_annualized_pct: Optional[float] = None
    trend_20_vs_50: Optional[str] = Field(
        None, description="Simple momentum orientation: 'bullish' (sma20 > sma50), 'bearish', or 'insufficient_data'"
    )
    latest_rsi_14: Optional[float] = Field(
        None, description="Latest 14-session Relative Strength Index (0-100)"
    )
    latest_volume_sma_20: Optional[float] = Field(
        None, description="Latest 20-session average volume"
    )
    latest_relative_volume: Optional[float] = Field(
        None, description="Latest relative volume ratio (Volume / Volume_SMA_20)"
    )
    close_vs_sma_20_pct: Optional[float] = Field(
        None, description="Percentage distance between latest close and 20-SMA"
    )
    close_vs_sma_50_pct: Optional[float] = Field(
        None, description="Percentage distance between latest close and 50-SMA"
    )
    sma_20_slope_5d: Optional[float] = Field(
        None, description="5-session percentage slope of SMA 20"
    )
    sma_50_slope_5d: Optional[float] = Field(
        None, description="5-session percentage slope of SMA 50"
    )


class CompanyInfo(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class MarketDataResponse(BaseModel):
    requested_ticker: str = Field(..., description="Original user/API requested symbol")
    provider_ticker: str = Field(..., description="Resolved provider symbol (e.g. TCS.NS)")
    provider: str = Field(default="Yahoo Finance (via yfinance daily historical)", description="Market data vendor")
    is_live_price: bool = Field(
        default=False,
        description="Explicit flag clarifying whether this data is guaranteed real-time (False for daily historical)",
    )
    price_series_convention: str = Field(
        default="raw_close",
        description="Price series convention used for returns and indicators. OHLC are raw unadjusted exchange prices.",
    )
    retrieval_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of data retrieval")
    latest_trading_date: Optional[str] = Field(None, description="Most recent trading session calendar date (YYYY-MM-DD)")
    latest_close: Optional[float] = Field(None, description="Most recent session closing price (raw unadjusted)")
    company: CompanyInfo = Field(default_factory=CompanyInfo, description="Company identity metadata if available")
    validation: ValidationResult = Field(..., description="Rigorous dataset audit and integrity status")
    indicators_summary: IndicatorSummary = Field(
        default_factory=IndicatorSummary, description="Latest snapshot of calculated indicators"
    )
    price_history: List[DailyBar] = Field(default_factory=list, description="Chronological daily OHLCV bars")
    indicator_series: List[IndicatorSeries] = Field(
        default_factory=list, description="Chronological technical indicators matched by date"
    )
