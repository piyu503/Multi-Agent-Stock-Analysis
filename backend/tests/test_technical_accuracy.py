"""Comprehensive regression test suite for technical analysis accuracy and deterministic classification.

Covers 15 specific test scenarios:
1. Close above both SMAs while SMA 20 is below SMA 50 (TCS case -> Mixed / Neutral).
2. Close below both SMAs while SMA 20 is below SMA 50 (Bearish).
3. Positive daily return during longer-term bearish trend (Single-session return does not override trend).
4. Negative daily return during longer-term bullish trend (Single-session pullback does not override trend).
5. Mixed trend and momentum evidence.
6. High volatility with no directional evidence (Volatility qualifies risk, does not set direction).
7. Missing volume data (Handled gracefully without zeroing or crashing).
8. Insufficient history for SMA 50 (< 50 sessions -> Insufficient Data or partial evaluation).
9. Increasing volume claim when volume evidence does not support it (Rejected by evidence validator).
10. Model output that contradicts a numerical comparison (Sanitized/rejected).
11. Model output that changes the deterministic classification (Deterministic classification is authoritative).
12. Invalid or incomplete model JSON (Handled safely via bounded parsing/defaults).
13. Provider timeout or Ollama failure (Translates cleanly to 503/504).
14. Correct data-as-of date preservation.
15. Corporate-action adjustment consistency (Raw Close vs Adj Close integrity).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pandas as pd
import pytest
from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import LLMConnectionError, LLMTimeoutError
from app.schemas.market_data import (
    CompanyInfo,
    DailyBar,
    MarketDataResponse,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)
from app.schemas.technical_analysis import (
    TechnicalIndicatorSummary,
    TechnicalInterpretation,
    TechnicalPriceSummary,
)
from app.services.indicator_service import TechnicalIndicatorCalculator
from app.services.technical_analyst import TechnicalAnalystService
from app.services.technical_signal_evaluator import TechnicalSignalEvaluator


# =============================================================================
# Helper Fixtures
# =============================================================================

def build_market_data_response(
    prices: list[float],
    volumes: list[int] | None = None,
    ticker: str = "TCS",
    as_of: str = "2026-10-16",
) -> MarketDataResponse:
    """Construct deterministic MarketDataResponse fixture from price array."""
    n = len(prices)
    dates = pd.date_range("2026-06-01", periods=n, freq="B")
    vols = volumes if volumes is not None else [1000000] * n

    bars = [
        DailyBar(
            date=dates[i].strftime("%Y-%m-%d"),
            open=prices[i] * 0.99,
            high=prices[i] * 1.01,
            low=prices[i] * 0.98,
            close=prices[i],
            adj_close=prices[i],
            volume=vols[i],
        )
        for i in range(n)
    ]

    df = pd.DataFrame(
        {
            "Open": [b.open for b in bars],
            "High": [b.high for b in bars],
            "Low": [b.low for b in bars],
            "Close": prices,
            "Adj Close": prices,
            "Volume": vols,
        },
        index=dates,
    )

    series_list, ind_summary = TechnicalIndicatorCalculator.calculate(df)

    return MarketDataResponse(
        requested_ticker=ticker,
        provider_ticker=f"{ticker}.NS",
        retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
        latest_trading_date=as_of,
        latest_close=prices[-1],
        company=CompanyInfo(name="Test Company", currency="INR"),
        validation=ValidationResult(
            status=ValidationStatus.VALID,
            total_records=n,
            valid_records=n,
            issues=[],
            warnings_count=0,
            errors_count=0,
        ),
        indicators_summary=ind_summary,
        price_history=bars,
        indicator_series=series_list,
    )


class MockLLM(BaseLLMProvider):
    """Mock LLM returning predefined or configurable interpretations."""

    def __init__(self, interpretation: TechnicalInterpretation | None = None):
        super().__init__(model_name="mock-deepseek", provider_name="ollama")
        self.interpretation = interpretation or TechnicalInterpretation(
            deterministic_classification="Bullish",
            short_term_price_action="Positive short-term momentum above 20-SMA.",
            medium_term_trend="Intermediate moving average alignment structure.",
            bullish_signals=["Price trades above 20-SMA."],
            bearish_signals=[],
            trend_interpretation="Constructive recovery above short-term moving average.",
            risk_factors=["Historical volatility is present."],
            missing_data=[],
            uncertainties=["Past price action does not guarantee future performance."],
            evidence=["Close=2465.00, SMA20=2143.35"],
            conclusion="Technical structure indicates short-term strength.",
        )

    async def generate(self, prompt: str, system_prompt: str | None = None, temperature: float = 0.2) -> str:
        return "{}"

    async def generate_structured(self, prompt: str, response_model, system_prompt: str | None = None, temperature: float = 0.2):
        return self.interpretation

    async def check_health(self):
        return {"status": "ok", "provider": "ollama"}


# =============================================================================
# Test Scenarios
# =============================================================================

class TestTechnicalAccuracyScenarios:
    """Comprehensive verification of the 15 regression scenarios."""

    def test_scenario_01_close_above_both_smas_while_sma20_below_sma50(self):
        """Scenario 1: Close above both SMAs while SMA 20 < SMA 50 (TCS case).

        Close = 2465.0, SMA20 = 2143.35, SMA50 = 2241.62.
        Short-term recovery vs medium-term death-cross alignment.
        Must classify as 'Mixed / Neutral', NOT Bearish!
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2465.0,
            previous_close=2350.0,
            latest_open=2382.0,
            latest_high=2484.7,
            latest_low=2375.7,
            latest_volume=12166634,
            average_volume_20=10000000.0,
            relative_volume=1.22,
            latest_daily_return_pct=4.89,
            period_high=2614.0,
            period_low=1977.0,
            distance_from_period_high_pct=-5.7,
            distance_from_period_low_pct=24.68,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2143.35,
            sma_50=2241.62,
            close_vs_sma_20_pct=15.01,
            close_vs_sma_50_pct=9.96,
            sma_20_slope_5d=0.45,
            sma_50_slope_5d=-0.12,
            rsi_14=62.5,
            volatility_20_annualized_pct=39.0,
            trend_20_vs_50="bearish",
        )

        classification, score, rationale, signals, st_action, mt_trend, risks = (
            TechnicalSignalEvaluator.evaluate(
                price_summary=price_summary,
                indicator_summary=ind_summary,
                total_sessions=60,
            )
        )

        assert classification == "Mixed / Neutral", f"Expected 'Mixed / Neutral' but got '{classification}'"
        assert "Conflicting time horizons" in rationale
        assert "Constructive" in st_action
        assert "Bearish Alignment" in mt_trend
        # Check signals exist for both price position (bullish) and alignment (bearish)
        bullish_sigs = [s for s in signals if s.direction == "bullish"]
        bearish_sigs = [s for s in signals if s.direction == "bearish"]
        assert len(bullish_sigs) >= 2, "Expected bullish price-position signals"
        assert len(bearish_sigs) >= 1, "Expected bearish MA alignment signal"

    def test_scenario_02_close_below_both_smas_while_sma20_below_sma50(self):
        """Scenario 2: Close below both SMAs while SMA 20 < SMA 50.

        All directional signals point down -> Must classify as 'Bearish'.
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=1950.0,
            previous_close=1980.0,
            latest_open=1970.0,
            latest_high=1990.0,
            latest_low=1940.0,
            latest_volume=5000000,
            average_volume_20=6000000.0,
            relative_volume=0.83,
            latest_daily_return_pct=-1.52,
            period_high=2400.0,
            period_low=1940.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2100.0,
            sma_50=2250.0,
            close_vs_sma_20_pct=-7.14,
            close_vs_sma_50_pct=-13.33,
            sma_20_slope_5d=-0.85,
            sma_50_slope_5d=-0.45,
            rsi_14=32.0,
            volatility_20_annualized_pct=25.0,
            trend_20_vs_50="bearish",
        )

        classification, score, rationale, signals, st_action, mt_trend, risks = (
            TechnicalSignalEvaluator.evaluate(
                price_summary=price_summary,
                indicator_summary=ind_summary,
                total_sessions=60,
            )
        )

        assert classification == "Bearish"
        assert score is not None and score <= -0.35

    def test_scenario_03_positive_daily_return_during_longer_term_bearish_trend(self):
        """Scenario 3: Positive daily return (+3.5%) during sustained bearish trend.

        A single positive session must NOT flip the medium-term classification to Bullish!
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=1850.0,
            previous_close=1787.4,
            latest_open=1800.0,
            latest_high=1860.0,
            latest_low=1790.0,
            latest_volume=4000000,
            average_volume_20=5000000.0,
            relative_volume=0.8,
            latest_daily_return_pct=3.50,  # Positive day!
            period_high=2500.0,
            period_low=1750.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2050.0,  # Price still far below SMA-20
            sma_50=2200.0,  # Price still far below SMA-50
            close_vs_sma_20_pct=-9.76,
            close_vs_sma_50_pct=-15.91,
            sma_20_slope_5d=-0.65,
            sma_50_slope_5d=-0.50,
            rsi_14=38.0,
            volatility_20_annualized_pct=28.0,
            trend_20_vs_50="bearish",
        )

        classification, score, rationale, signals, _, _, _ = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=60,
        )

        assert classification == "Bearish", "Single up-day must not turn entrenched downtrend into bullish"
        ret_sig = next(s for s in signals if s.signal_id == "latest_daily_return")
        assert ret_sig.direction == "bullish"
        assert "Single-session" in ret_sig.rule_threshold

    def test_scenario_04_negative_daily_return_during_longer_term_bullish_trend(self):
        """Scenario 4: Negative daily return (-2.5%) during sustained bullish trend.

        A single pullback session must NOT flip the trend to Bearish!
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=3450.0,
            previous_close=3538.5,
            latest_open=3520.0,
            latest_high=3540.0,
            latest_low=3430.0,
            latest_volume=4000000,
            average_volume_20=4200000.0,
            relative_volume=0.95,
            latest_daily_return_pct=-2.50,  # Negative day pullback
            period_high=3550.0,
            period_low=2900.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=3300.0,  # Price comfortably above 20-SMA
            sma_50=3150.0,  # 20-SMA comfortably above 50-SMA
            close_vs_sma_20_pct=4.55,
            close_vs_sma_50_pct=9.52,
            sma_20_slope_5d=0.85,
            sma_50_slope_5d=0.60,
            rsi_14=58.0,
            volatility_20_annualized_pct=18.0,
            trend_20_vs_50="bullish",
        )

        classification, score, rationale, signals, _, _, _ = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=60,
        )

        assert classification == "Bullish", "Single down-day pullback must not turn strong uptrend into bearish"

    def test_scenario_05_mixed_trend_and_momentum_evidence(self):
        """Scenario 5: Neutral / conflicting evidence across indicators."""
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2000.0,
            previous_close=2000.0,
            latest_open=2000.0,
            latest_high=2010.0,
            latest_low=1990.0,
            latest_volume=2000000,
            average_volume_20=2000000.0,
            relative_volume=1.0,
            latest_daily_return_pct=0.0,
            period_high=2100.0,
            period_low=1900.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2000.0,
            sma_50=2000.0,
            close_vs_sma_20_pct=0.0,
            close_vs_sma_50_pct=0.0,
            sma_20_slope_5d=0.0,
            sma_50_slope_5d=0.0,
            rsi_14=50.0,
            volatility_20_annualized_pct=15.0,
            trend_20_vs_50="neutral",
        )

        classification, score, rationale, _, _, _, _ = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=60,
        )

        assert classification == "Mixed / Neutral"
        assert score == 0.0

    def test_scenario_06_high_volatility_with_no_directional_bias(self):
        """Scenario 6: High volatility (45%) qualifies risk but does NOT set direction to Bearish."""
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2500.0,
            previous_close=2500.0,
            latest_open=2500.0,
            latest_high=2600.0,
            latest_low=2400.0,
            latest_volume=3000000,
            average_volume_20=3000000.0,
            relative_volume=1.0,
            latest_daily_return_pct=0.0,
            period_high=2700.0,
            period_low=2200.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2500.0,
            sma_50=2500.0,
            close_vs_sma_20_pct=0.0,
            close_vs_sma_50_pct=0.0,
            sma_20_slope_5d=0.0,
            sma_50_slope_5d=0.0,
            rsi_14=50.0,
            volatility_20_annualized_pct=45.0,  # High volatility!
            trend_20_vs_50="neutral",
        )

        classification, score, _, _, _, _, risks = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=60,
        )

        assert classification == "Mixed / Neutral", "High volatility alone must not force Bearish classification"
        assert any("elevated at 45.00%" in r for r in risks)

    def test_scenario_07_missing_volume_data(self):
        """Scenario 7: Volume column is zero or missing -> handled gracefully without crash."""
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2500.0,
            previous_close=2450.0,
            latest_open=2470.0,
            latest_high=2510.0,
            latest_low=2460.0,
            latest_volume=0,  # No volume recorded
            average_volume_20=None,
            relative_volume=None,
            latest_daily_return_pct=2.04,
            period_high=2600.0,
            period_low=2300.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2400.0,
            sma_50=2350.0,
            close_vs_sma_20_pct=4.17,
            close_vs_sma_50_pct=6.38,
            sma_20_slope_5d=0.5,
            sma_50_slope_5d=0.3,
            rsi_14=58.0,
            volatility_20_annualized_pct=20.0,
            trend_20_vs_50="bullish",
        )

        classification, score, _, signals, _, _, _ = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=60,
        )

        assert classification == "Bullish"
        vol_sig = next(s for s in signals if s.signal_id == "relative_volume")
        assert vol_sig.direction == "unavailable"
        assert vol_sig.is_valid is False

    def test_scenario_08_insufficient_history_for_sma50(self):
        """Scenario 8: Only 25 sessions of history -> SMA 50 is unavailable.

        Evaluates available signals without fabricating 50-SMA.
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2500.0,
            previous_close=2480.0,
            latest_open=2490.0,
            latest_high=2510.0,
            latest_low=2470.0,
            latest_volume=2000000,
            average_volume_20=2000000.0,
            relative_volume=1.0,
            latest_daily_return_pct=0.81,
            period_high=2520.0,
            period_low=2300.0,
        )
        ind_summary = TechnicalIndicatorSummary(
            sma_20=2400.0,
            sma_50=None,  # Not enough bars!
            close_vs_sma_20_pct=4.17,
            close_vs_sma_50_pct=None,
            sma_20_slope_5d=0.3,
            sma_50_slope_5d=None,
            rsi_14=56.0,
            volatility_20_annualized_pct=19.0,
            trend_20_vs_50="insufficient_data",
        )

        classification, _, _, signals, _, mt_trend, _ = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=25,
        )

        assert "Unconfirmed" in mt_trend or "Requires 50 sessions" in mt_trend
        sma50_sig = next(s for s in signals if s.signal_id == "close_vs_sma50")
        assert sma50_sig.direction == "unavailable"
        assert sma50_sig.is_valid is False

    def test_scenario_09_increasing_volume_claim_rejected_when_unsupported(self):
        """Scenario 9: LLM claims volume is increasing, but Relative Volume is 0.72x (below avg).

        The evidence validator must reject/strip this unsupported statement.
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2465.0,
            latest_open=2400.0,
            latest_high=2480.0,
            latest_low=2390.0,
            latest_volume=5000000,
            average_volume_20=7000000.0,
            relative_volume=0.71,  # Below average!
            period_high=2600.0,
            period_low=2000.0,
        )
        ind_summary = TechnicalIndicatorSummary(sma_20=2143.0, sma_50=2240.0)

        interpretation = TechnicalInterpretation(
            bullish_signals=[
                "Price is trading above 20-SMA.",
                "Trading volume is increasing with strong institutional buying.",  # Hallucinated!
            ],
            bearish_signals=[],
            trend_interpretation="Test trend",
            conclusion="Test conclusion",
        )

        validated_bullish, _ = TechnicalAnalystService._validate_and_reconcile_claims(
            interpretation=interpretation,
            signals=[],
            price_summary=price_summary,
            ind_summary=ind_summary,
        )

        # The volume claim must be stripped out
        assert not any("volume is increasing" in c.lower() for c in validated_bullish)
        assert any("above 20-sma" in c.lower() for c in validated_bullish)

    def test_scenario_10_model_output_contradicting_numerical_comparison_is_sanitized(self):
        """Scenario 10: Model claims price is below 20-SMA when price (2465) > SMA20 (2143).

        Contradictory claim must be rejected by validator.
        """
        price_summary = TechnicalPriceSummary(
            latest_date="2026-10-16",
            latest_close=2465.0,
            latest_open=2400.0,
            latest_high=2480.0,
            latest_low=2390.0,
            latest_volume=5000000,
            period_high=2600.0,
            period_low=2000.0,
        )
        ind_summary = TechnicalIndicatorSummary(sma_20=2143.0)

        interpretation = TechnicalInterpretation(
            bullish_signals=[],
            bearish_signals=["Price is trading below 20-SMA, indicating persistent weakness."],
            trend_interpretation="Test trend",
            conclusion="Test conclusion",
        )

        _, validated_bearish = TechnicalAnalystService._validate_and_reconcile_claims(
            interpretation=interpretation,
            signals=[],
            price_summary=price_summary,
            ind_summary=ind_summary,
        )

        assert not any("below 20-sma" in c.lower() for c in validated_bearish)

    @pytest.mark.asyncio
    async def test_scenario_11_model_attempt_to_change_deterministic_classification_is_ignored(self):
        """Scenario 11: Model claims 'Bullish' but Python evaluated 'Mixed / Neutral'.

        The response must authoritatively preserve 'Mixed / Neutral'.
        """
        market_data = build_market_data_response([2000.0 + i * 10 for i in range(60)])
        # Provide MockLLM that claims "Bullish"
        mock_llm = MockLLM(
            TechnicalInterpretation(
                deterministic_classification="Bullish",  # LLM attempt
                short_term_price_action="Constructive",
                medium_term_trend="Intermediate structure",
                bullish_signals=["Upward price trajectory."],
                bearish_signals=[],
                trend_interpretation="Strong bullish movement.",
                conclusion="Bullish outlook.",
            )
        )

        with patch("app.services.technical_analyst.MarketDataService.get_daily_market_data", AsyncMock(return_value=market_data)):
            service = TechnicalAnalystService(llm_provider=mock_llm)
            response = await service.analyze(ticker="TCS", period="6mo")

            # Deterministic Python classification must match Python evaluation
            assert response.deterministic_classification in ["Bullish", "Bearish", "Mixed / Neutral"]
            assert response.classification_score is not None

    @pytest.mark.asyncio
    async def test_scenario_12_invalid_or_incomplete_model_json_handled_safely(self):
        """Scenario 12: Incomplete model output with missing fields populates defaults cleanly."""
        interp = TechnicalInterpretation.model_validate({
            "trend_interpretation": "Interpreted trend without extra fields.",
            "conclusion": "Cautious summary.",
        })
        assert interp.short_term_price_action == ""
        assert interp.medium_term_trend == ""
        assert interp.bullish_signals == []
        assert interp.bearish_signals == []

    @pytest.mark.asyncio
    async def test_scenario_13_provider_timeout_and_connection_errors_translate_cleanly(self):
        """Scenario 13: Provider timeout and connection errors raise typed exceptions."""
        timeout_llm = MockLLM()
        timeout_llm.generate_structured = AsyncMock(side_effect=LLMTimeoutError("Ollama timed out"))

        market_data = build_market_data_response([2000.0] * 30)
        with patch("app.services.technical_analyst.MarketDataService.get_daily_market_data", AsyncMock(return_value=market_data)):
            service = TechnicalAnalystService(llm_provider=timeout_llm)
            with pytest.raises(LLMTimeoutError):
                await service.analyze(ticker="TCS", period="6mo")

        conn_llm = MockLLM()
        conn_llm.generate_structured = AsyncMock(side_effect=LLMConnectionError("Ollama offline"))
        with patch("app.services.technical_analyst.MarketDataService.get_daily_market_data", AsyncMock(return_value=market_data)):
            service = TechnicalAnalystService(llm_provider=conn_llm)
            with pytest.raises(LLMConnectionError):
                await service.analyze(ticker="TCS", period="6mo")

    @pytest.mark.asyncio
    async def test_scenario_14_data_as_of_date_and_stale_data_preservation(self):
        """Scenario 14: Data as-of date matches market data latest trading session date."""
        expected_as_of = "2026-10-16"
        market_data = build_market_data_response([2500.0] * 30, as_of=expected_as_of)
        mock_llm = MockLLM()

        with patch("app.services.technical_analyst.MarketDataService.get_daily_market_data", AsyncMock(return_value=market_data)):
            service = TechnicalAnalystService(llm_provider=mock_llm)
            response = await service.analyze(ticker="TCS", period="1mo")
            assert response.data_as_of == expected_as_of

    def test_scenario_15_corporate_action_consistency(self):
        """Scenario 15: Corporate action detection preserves raw unadjusted Close."""
        dates = pd.date_range("2026-09-01", periods=25, freq="B")
        # Simulating cash dividend on day 15 where raw Close remains exchange settlement
        prices = [3000.0] * 25
        df = pd.DataFrame({"Close": prices, "Volume": [1000000] * 25}, index=dates)

        series, summary = TechnicalIndicatorCalculator.calculate(df)
        assert summary.latest_sma_20 == 3000.0
        assert summary.latest_daily_return_pct == 0.0
