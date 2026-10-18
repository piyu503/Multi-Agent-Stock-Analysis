"""Technical Stock Analyst service consuming market data and orchestrating LLM interpretation."""

from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
from app.core.llm.base import BaseLLMProvider
from app.core.llm.factory import get_llm_provider
from app.core.logging import get_logger
from app.schemas.market_data import ValidationStatus
from app.schemas.technical_analysis import (
    DeterministicSignal,
    TechnicalAnalysisResponse,
    TechnicalIndicatorSummary,
    TechnicalInterpretation,
    TechnicalPriceSummary,
)
from app.services.market_data_service import MarketDataService
from app.services.technical_signal_evaluator import TechnicalSignalEvaluator

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the technical-analysis explanation component of TradeRunner.

Your job is to explain the supplied, precomputed evidence accurately. You do not independently recalculate financial indicators or replace the deterministic classification.

Rules:
1. Use only the supplied observations and evidence.
2. Treat numerical values and deterministic signals as authoritative inputs.
3. Never invent prices, returns, indicator values, volume changes, support/resistance levels, news, events, or citations.
4. Do not claim that volume increased unless the supplied volume evidence explicitly supports that statement.
5. Do not describe a stock as above or below a moving average contrary to the supplied numerical comparison.
6. Explain short-term price action separately from medium-term trend.
7. Distinguish price position, moving-average alignment, momentum, volatility, and volume confirmation.
8. Explicitly explain conflicts between signals.
9. A positive daily return is evidence for the latest session, not proof of a bullish trend.
10. A close above SMA 20 and SMA 50 is positive price-position evidence even if SMA 20 is below SMA 50.
11. High volatility indicates elevated price variability and risk; it is not automatically bullish or bearish.
12. If evidence is insufficient, state that it is insufficient.
13. Do not manufacture a bullish or bearish case when the evidence is mixed.
14. Do not produce an unsupported numerical confidence score or probability of profit.
15. Do not guarantee future prices or returns.
16. Keep the explanation concise, specific, and traceable to the provided evidence.
17. Do not expose hidden internal reasoning. Think very briefly in fewer than 50 words, then proceed directly to outputting the JSON object with brief, evidence-backed explanations.

Return the required schema only. Do not change the deterministic classification.
"""


class TechnicalAnalystService:
    """Orchestrates deterministic market data retrieval, prompt preparation, and LLM interpretation."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None) -> None:
        self.provider = llm_provider or get_llm_provider()

    async def analyze(
        self,
        ticker: str,
        period: str = "6mo",
    ) -> TechnicalAnalysisResponse:
        """Execute end-to-end technical analysis pipeline for target ticker."""
        # 1. Fetch validated market data using existing MarketDataService
        market_data = await MarketDataService.get_daily_market_data(ticker=ticker, period=period)

        if market_data.validation.status == ValidationStatus.INVALID or not market_data.price_history:
            issue_msgs = "; ".join(i.message for i in market_data.validation.issues)
            raise ValueError(f"Cannot perform technical analysis on invalid market data for '{ticker}': {issue_msgs}")

        # 2. Build deterministic price summary
        latest_bar = market_data.price_history[-1]
        prev_bar = market_data.price_history[-2] if len(market_data.price_history) >= 2 else None
        all_highs = [b.high for b in market_data.price_history]
        all_lows = [b.low for b in market_data.price_history]
        period_high = max(all_highs) if all_highs else latest_bar.high
        period_low = min(all_lows) if all_lows else latest_bar.low

        dist_high = ((latest_bar.close - period_high) / period_high) * 100.0 if period_high > 0 else 0.0
        dist_low = ((latest_bar.close - period_low) / period_low) * 100.0 if period_low > 0 else 0.0

        price_summary = TechnicalPriceSummary(
            latest_date=latest_bar.date,
            latest_close=latest_bar.close,
            previous_close=prev_bar.close if prev_bar else None,
            latest_open=latest_bar.open,
            latest_high=latest_bar.high,
            latest_low=latest_bar.low,
            latest_volume=latest_bar.volume,
            average_volume_20=market_data.indicators_summary.latest_volume_sma_20,
            relative_volume=market_data.indicators_summary.latest_relative_volume,
            latest_daily_return_pct=market_data.indicators_summary.latest_daily_return_pct,
            period_high=period_high,
            period_low=period_low,
            distance_from_period_high_pct=round(dist_high, 2),
            distance_from_period_low_pct=round(dist_low, 2),
        )

        # 3. Build deterministic indicator summary
        ind_summary = TechnicalIndicatorSummary(
            sma_20=market_data.indicators_summary.latest_sma_20,
            sma_50=market_data.indicators_summary.latest_sma_50,
            close_vs_sma_20_pct=market_data.indicators_summary.close_vs_sma_20_pct,
            close_vs_sma_50_pct=market_data.indicators_summary.close_vs_sma_50_pct,
            sma_20_slope_5d=market_data.indicators_summary.sma_20_slope_5d,
            sma_50_slope_5d=market_data.indicators_summary.sma_50_slope_5d,
            rsi_14=market_data.indicators_summary.latest_rsi_14,
            volatility_20_annualized_pct=market_data.indicators_summary.latest_volatility_20_annualized_pct,
            trend_20_vs_50=market_data.indicators_summary.trend_20_vs_50,
        )

        # 4. Evaluate deterministic signals and authoritative classification
        (
            det_classification,
            det_score,
            det_rationale,
            det_signals,
            st_action,
            mt_trend,
            det_risks,
        ) = TechnicalSignalEvaluator.evaluate(
            price_summary=price_summary,
            indicator_summary=ind_summary,
            total_sessions=len(market_data.price_history),
        )

        # 5. Construct compact, factual prompt for the LLM
        prompt = self._build_prompt(
            market_data=market_data,
            price_summary=price_summary,
            ind_summary=ind_summary,
            det_classification=det_classification,
            det_score=det_score,
            det_rationale=det_rationale,
            det_signals=det_signals,
            st_action=st_action,
            mt_trend=mt_trend,
        )

        # 6. Call configured LLM provider for structured interpretation
        logger.info(
            f"Invoking LLM provider '{self.provider.provider_name}' ({self.provider.model_name}) "
            f"for technical analysis of {market_data.provider_ticker}"
        )

        interpretation = await self.provider.generate_structured(
            prompt=prompt,
            response_model=TechnicalInterpretation,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
        )

        # 7. Post-generation evidence validation: Enforce classification authority & audit claims
        validated_bullish, validated_bearish = self._validate_and_reconcile_claims(
            interpretation=interpretation,
            signals=det_signals,
            price_summary=price_summary,
            ind_summary=ind_summary,
        )

        # Merge risk factors
        merged_risks = list(dict.fromkeys(det_risks + interpretation.risk_factors))

        # 8. Assemble complete, verified response
        return TechnicalAnalysisResponse(
            ticker=market_data.requested_ticker,
            resolved_ticker=market_data.provider_ticker,
            company_name=market_data.company.name,
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            data_as_of=market_data.latest_trading_date or latest_bar.date,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            deterministic_classification=det_classification,  # Authoritative Python output!
            classification_score=det_score,
            classification_rationale=det_rationale,
            deterministic_signals=det_signals,
            short_term_price_action=interpretation.short_term_price_action or st_action,
            medium_term_trend=interpretation.medium_term_trend or mt_trend,
            price_summary=price_summary,
            indicator_summary=ind_summary,
            bullish_signals=validated_bullish,
            bearish_signals=validated_bearish,
            trend_interpretation=interpretation.trend_interpretation,
            risk_factors=merged_risks,
            missing_data=interpretation.missing_data,
            uncertainties=interpretation.uncertainties,
            evidence=interpretation.evidence,
            conclusion=interpretation.conclusion,
        )

    @classmethod
    def _validate_and_reconcile_claims(
        cls,
        interpretation: TechnicalInterpretation,
        signals: List[DeterministicSignal],
        price_summary: TechnicalPriceSummary,
        ind_summary: TechnicalIndicatorSummary,
    ) -> Tuple[List[str], List[str]]:
        """Validate LLM signal claims against verified deterministic evidence."""
        det_bullish = [s.explanation for s in signals if s.direction == "bullish" and s.is_valid]
        det_bearish = [s.explanation for s in signals if s.direction == "bearish" and s.is_valid]

        # 1. Clean LLM bullish signals
        cleaned_bullish: List[str] = []
        for claim in interpretation.bullish_signals:
            if not isinstance(claim, str) or not claim.strip():
                continue
            claim_lower = claim.lower()

            # Rule: Do not claim volume is increasing unless relative volume >= 1.0 and valid
            if "volume is increasing" in claim_lower or "volume increased" in claim_lower or "increasing volume" in claim_lower:
                if price_summary.relative_volume is None or price_summary.relative_volume < 1.0:
                    logger.warning(f"Rejecting unsupported LLM volume claim: {claim}")
                    continue

            # Rule: Do not contradict moving average numerical comparison
            if "above 20-sma" in claim_lower or "above the 20-day" in claim_lower or "above 20-day" in claim_lower:
                if ind_summary.sma_20 is not None and price_summary.latest_close < ind_summary.sma_20:
                    logger.warning(f"Rejecting contradicted MA comparison in bullish signals: {claim}")
                    continue

            # Rule: Do not claim near highs if far from high
            if "near its recent high" in claim_lower or "near recent high" in claim_lower:
                if price_summary.distance_from_period_high_pct is not None and abs(price_summary.distance_from_period_high_pct) > 10.0:
                    logger.warning(f"Rejecting unsupported near-high claim: {claim}")
                    continue

            # Remove empty or trivial claims
            if "no strong bullish" in claim_lower:
                continue

            cleaned_bullish.append(claim)

        # 2. Clean LLM bearish signals
        cleaned_bearish: List[str] = []
        for claim in interpretation.bearish_signals:
            if not isinstance(claim, str) or not claim.strip():
                continue
            claim_lower = claim.lower()

            # Rule: Do not contradict moving average numerical comparison
            if "below 20-sma" in claim_lower or "below the 20-day" in claim_lower or "below 20-day" in claim_lower:
                if ind_summary.sma_20 is not None and price_summary.latest_close > ind_summary.sma_20:
                    logger.warning(f"Rejecting contradicted MA comparison in bearish signals: {claim}")
                    continue

            if "no dominant bearish" in claim_lower:
                continue

            cleaned_bearish.append(claim)

        # 3. Grounding Fallback: If model missed valid deterministic signals, populate them
        final_bullish = cleaned_bullish if cleaned_bullish else det_bullish
        final_bearish = cleaned_bearish if cleaned_bearish else det_bearish

        return final_bullish, final_bearish

    @staticmethod
    def _build_prompt(
        market_data,
        price_summary: TechnicalPriceSummary,
        ind_summary: TechnicalIndicatorSummary,
        det_classification: str,
        det_score: Optional[float],
        det_rationale: str,
        det_signals: List[DeterministicSignal],
        st_action: str,
        mt_trend: str,
    ) -> str:
        """Create a compact, factual prompt providing authoritative precomputed evidence."""
        recent_bars = market_data.price_history[-5:]
        recent_str = "\n".join(
            f"  - {b.date}: Close=INR {b.close:.2f}, Volume={b.volume:,}"
            for b in recent_bars
        )

        signals_str = "\n".join(
            f"  - [{s.category.upper()}] {s.name}: {s.direction.upper()} ({s.display_value}) -> {s.explanation}"
            for s in det_signals
        )

        return f"""TECHNICAL EVIDENCE DOSSIER FOR {market_data.provider_ticker} ({market_data.company.name or 'NSE Equity'}):

FACTS:
- As-Of Date: {price_summary.latest_date}
- Latest Close: INR {price_summary.latest_close:.2f}
- Previous Close: {f"INR {price_summary.previous_close:.2f}" if price_summary.previous_close else "N/A"}
- Latest Session Return: {f"{price_summary.latest_daily_return_pct:+.2f}%" if price_summary.latest_daily_return_pct is not None else "N/A"} (Single session only)
- Traded Volume: {price_summary.latest_volume:,}
- 20-Day Average Volume: {f"{price_summary.average_volume_20:,.0f}" if price_summary.average_volume_20 else "Unavailable"}
- Relative Volume: {f"{price_summary.relative_volume:.2f}x" if price_summary.relative_volume is not None else "Unavailable"}
- Period High / Low: High = INR {price_summary.period_high:.2f} ({price_summary.distance_from_period_high_pct:+.2f}%), Low = INR {price_summary.period_low:.2f} ({price_summary.distance_from_period_low_pct:+.2f}%)

DETERMINISTIC INDICATORS:
- 20-Day Simple Moving Average (SMA-20): {f"INR {ind_summary.sma_20:.2f} (Close is {ind_summary.close_vs_sma_20_pct:+.2f}% vs SMA-20)" if ind_summary.sma_20 else "Unavailable (requires 20 bars)"}
- 50-Day Simple Moving Average (SMA-50): {f"INR {ind_summary.sma_50:.2f} (Close is {ind_summary.close_vs_sma_50_pct:+.2f}% vs SMA-50)" if ind_summary.sma_50 else "Unavailable (requires 50 bars)"}
- 20-SMA 5-Day Slope: {f"{ind_summary.sma_20_slope_5d:+.2f}%" if ind_summary.sma_20_slope_5d is not None else "Unavailable"}
- 14-Session RSI: {f"{ind_summary.rsi_14:.2f}" if ind_summary.rsi_14 is not None else "Unavailable"}
- 20-Session Annualized Volatility: {f"{ind_summary.volatility_20_annualized_pct:.2f}%" if ind_summary.volatility_20_annualized_pct else "Unavailable"}

AUTHORITATIVE DETERMINISTIC CLASSIFICATION (PYTHON COMPUTED):
- Classification: {det_classification}
- Conviction Score: {f"{det_score:+.2f}" if det_score is not None else "N/A"}
- Rationale: {det_rationale}
- Short-Term Price Action: {st_action}
- Medium-Term Trend: {mt_trend}

PRECOMPUTED DETERMINISTIC SIGNALS:
{signals_str}

RECENT 5 SESSIONS:
{recent_str}

INSTRUCTIONS FOR JSON GENERATION:
1. Explain the precomputed facts. Do not recalculate or alter the deterministic classification ({det_classification}).
2. Distinguish short-term price action from medium-term trend alignment.
3. If price is above SMAs while SMA-20 < SMA-50, clearly explain this structural divergence as mixed evidence across timeframes.
4. Output valid JSON matching the TechnicalInterpretation schema.
"""
