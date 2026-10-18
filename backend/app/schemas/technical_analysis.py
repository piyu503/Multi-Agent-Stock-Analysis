"""Pydantic schemas for technical stock analysis requests, deterministic summaries, and LLM interpretation."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class TechnicalAnalysisRequest(BaseModel):
    """Request payload for running technical analysis on an equity ticker."""

    ticker: str = Field(
        ...,
        description="Target equity ticker symbol (e.g. 'TCS', 'TCS.NS', 'INFY')",
        min_length=1,
        max_length=30,
    )
    period: Literal["1mo", "3mo", "6mo", "1y", "2y"] = Field(
        default="6mo",
        description="Historical price timeframe for indicator calculation",
    )


class DeterministicSignal(BaseModel):
    """Structured deterministic signal evaluated directly from verified market data."""

    signal_id: str = Field(..., description="Unique machine-readable identifier for signal")
    name: str = Field(..., description="Human-readable signal title")
    category: Literal["price_position", "trend_alignment", "momentum", "volume"] = Field(
        ..., description="Signal grouping category"
    )
    direction: Literal["bullish", "bearish", "neutral", "unavailable"] = Field(
        ..., description="Directional polarity of the signal"
    )
    numerical_observation: Optional[float] = Field(None, description="Key numerical observation value")
    display_value: str = Field(..., description="Readable formatted value")
    rule_threshold: str = Field(..., description="Deterministic decision threshold or comparison rule")
    explanation: str = Field(..., description="Short factual explanation")
    evidence_ref: str = Field(..., description="Exact reference to input data points")
    is_valid: bool = Field(default=True, description="Whether signal has sufficient underlying history")


class TechnicalPriceSummary(BaseModel):
    """Deterministic snapshot of recent price action."""

    latest_date: str = Field(..., description="Date of the latest recorded trading session (YYYY-MM-DD)")
    latest_close: float = Field(..., description="Latest session closing price in INR")
    previous_close: Optional[float] = Field(None, description="Previous session closing price in INR")
    latest_open: float = Field(..., description="Latest session opening price in INR")
    latest_high: float = Field(..., description="Latest session high in INR")
    latest_low: float = Field(..., description="Latest session low in INR")
    latest_volume: int = Field(..., description="Latest session traded volume")
    average_volume_20: Optional[float] = Field(None, description="20-session average traded volume")
    relative_volume: Optional[float] = Field(None, description="Ratio of latest volume to 20-session average")
    latest_daily_return_pct: Optional[float] = Field(None, description="Percentage return of latest session")
    period_high: float = Field(..., description="Highest price over analyzed period")
    period_low: float = Field(..., description="Lowest price over analyzed period")
    distance_from_period_high_pct: Optional[float] = Field(None, description="Percentage distance from period high")
    distance_from_period_low_pct: Optional[float] = Field(None, description="Percentage distance from period low")


class TechnicalIndicatorSummary(BaseModel):
    """Deterministic indicator calculations."""

    sma_20: Optional[float] = Field(None, description="20-session simple moving average")
    sma_50: Optional[float] = Field(None, description="50-session simple moving average")
    close_vs_sma_20_pct: Optional[float] = Field(None, description="Percentage distance from close to SMA-20")
    close_vs_sma_50_pct: Optional[float] = Field(None, description="Percentage distance from close to SMA-50")
    sma_20_slope_5d: Optional[float] = Field(None, description="5-session percentage slope of SMA-20")
    sma_50_slope_5d: Optional[float] = Field(None, description="5-session percentage slope of SMA-50")
    rsi_14: Optional[float] = Field(None, description="14-session Relative Strength Index (0-100)")
    volatility_20_annualized_pct: Optional[float] = Field(
        None, description="20-session annualized historical volatility percentage"
    )
    trend_20_vs_50: Optional[str] = Field(None, description="Moving average orientation: 'bullish', 'bearish', or 'insufficient_data'")


class TechnicalInterpretation(BaseModel):
    """Structured LLM interpretation of deterministic market evidence."""

    deterministic_classification: Optional[str] = Field(
        None,
        description="Authoritative deterministic classification ('Bullish', 'Bearish', 'Mixed / Neutral', 'Insufficient Data')",
    )
    short_term_price_action: str = Field(
        default="",
        description="Factual assessment of immediate price action, return, and position relative to 20-SMA",
    )
    medium_term_trend: str = Field(
        default="",
        description="Factual assessment of broader trend structure, moving average alignment (SMA-20 vs SMA-50)",
    )
    bullish_signals: List[str] = Field(
        default_factory=list,
        description="Observed bullish technical patterns or momentum signals grounded in verified data",
    )
    bearish_signals: List[str] = Field(
        default_factory=list,
        description="Observed bearish technical warning signs or momentum breakdowns grounded in verified data",
    )
    trend_interpretation: str = Field(
        default="",
        description="Synthesis explaining short-term vs medium-term dynamics and reconciling conflicts",
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Key risk considerations (e.g. elevated volatility, wide trading spreads)",
    )
    missing_data: List[str] = Field(
        default_factory=list,
        description="Identified data limitations (e.g. unavailable 50-SMA due to limited history)",
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Explicit uncertainties regarding technical interpretation or market conditions",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Specific citations to input indicators and price points supporting the findings",
    )
    conclusion: str = Field(
        default="",
        description="Cautious, backward-looking technical summary with explicit financial disclaimer",
    )


class TechnicalAnalysisResponse(BaseModel):
    """Complete, verified response returned by the technical analyst endpoint."""

    ticker: str = Field(..., description="Requested ticker symbol")
    resolved_ticker: str = Field(..., description="Resolved provider symbol (e.g. TCS.NS)")
    company_name: Optional[str] = Field(None, description="Company corporate name if reliably resolved")
    analysis_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of analysis execution")
    data_as_of: str = Field(..., description="Date of the latest market session analyzed (YYYY-MM-DD)")
    provider: str = Field(..., description="Name of LLM provider used (e.g. 'ollama', 'gemini')")
    model: str = Field(..., description="Name of LLM model used (e.g. 'deepseek-r1:7b')")
    deterministic_classification: Literal["Bullish", "Bearish", "Mixed / Neutral", "Insufficient Data"] = Field(
        ..., description="Authoritative Python-evaluated overall classification"
    )
    classification_score: Optional[float] = Field(
        None, description="Transparent aggregated technical conviction score between -1.0 (bearish) and +1.0 (bullish)"
    )
    classification_rationale: str = Field(
        ..., description="Deterministic explanation of why this classification was assigned"
    )
    deterministic_signals: List[DeterministicSignal] = Field(
        default_factory=list, description="Collection of individual deterministic signals evaluated from data"
    )
    short_term_price_action: str = Field(..., description="Summary of short-term price position and return")
    medium_term_trend: str = Field(..., description="Summary of medium-term trend and moving average alignment")
    price_summary: TechnicalPriceSummary = Field(..., description="Deterministic price action summary")
    indicator_summary: TechnicalIndicatorSummary = Field(..., description="Deterministic technical indicators")
    bullish_signals: List[str] = Field(default_factory=list, description="Observed bullish signals")
    bearish_signals: List[str] = Field(default_factory=list, description="Observed bearish signals")
    trend_interpretation: str = Field(..., description="Factual trend interpretation")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    missing_data: List[str] = Field(default_factory=list, description="Identified missing data or limitations")
    uncertainties: List[str] = Field(default_factory=list, description="Analytical uncertainties")
    evidence: List[str] = Field(default_factory=list, description="Factual evidence references")
    conclusion: str = Field(..., description="Cautious, non-prescriptive technical conclusion")
    disclaimer: str = Field(
        default=(
            "Informational technical analysis based solely on historical market data. "
            "Not personalized financial advice, investment recommendation, or automated trading instruction."
        ),
        description="Compliance and financial disclaimer",
    )
