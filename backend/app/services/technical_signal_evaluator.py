"""Deterministic Technical Signal Evaluator.

Performs auditable, rule-based signal evaluation and transparent classification.
Does not rely on LLM arithmetic, prevents double-counting, and explicitly handles
conflicting signals across short-term and medium-term timeframes.
"""

from typing import Dict, List, Optional, Tuple
from app.schemas.technical_analysis import (
    DeterministicSignal,
    TechnicalIndicatorSummary,
    TechnicalPriceSummary,
)


class TechnicalSignalEvaluator:
    """Evaluates deterministic technical signals and computes authoritative classification."""

    CATEGORY_WEIGHTS: Dict[str, float] = {
        "price_position": 0.30,
        "trend_alignment": 0.30,
        "momentum": 0.25,
        "volume": 0.15,
    }

    @classmethod
    def evaluate(
        cls,
        price_summary: TechnicalPriceSummary,
        indicator_summary: TechnicalIndicatorSummary,
        total_sessions: int,
    ) -> Tuple[str, Optional[float], str, List[DeterministicSignal], str, str, List[str]]:
        """Evaluate deterministic signals from price and indicator summaries.

        Returns:
            Tuple of:
            - classification: 'Bullish', 'Bearish', 'Mixed / Neutral', or 'Insufficient Data'
            - classification_score: float between -1.0 and +1.0 (or None if insufficient data)
            - classification_rationale: Detailed human-readable explanation of the score and classification
            - signals: List[DeterministicSignal]
            - short_term_price_action: Factual summary of short-term action
            - medium_term_trend: Factual summary of medium-term trend
            - risk_factors: List of deterministic risk factors
        """
        signals: List[DeterministicSignal] = []
        risk_factors: List[str] = []

        close = price_summary.latest_close
        sma_20 = indicator_summary.sma_20
        sma_50 = indicator_summary.sma_50
        daily_ret = price_summary.latest_daily_return_pct
        rsi = indicator_summary.rsi_14
        rel_vol = price_summary.relative_volume
        vol_ann = indicator_summary.volatility_20_annualized_pct

        # Insufficient data check: require at least 20 sessions for basic technical analysis
        if total_sessions < 20 or sma_20 is None:
            rationale = f"Analyzed period contains only {total_sessions} sessions (< 20). 20-session SMA and volatility unavailable."
            return (
                "Insufficient Data",
                None,
                rationale,
                [],
                "Insufficient price history to determine short-term price position.",
                "Insufficient price history to determine medium-term trend.",
                ["Dataset contains fewer than 20 sessions; statistical and indicator calculations are constrained."],
            )

        # -------------------------------------------------------------------------
        # Category 1: Price Position (Close vs SMAs)
        # -------------------------------------------------------------------------
        price_position_scores: List[float] = []

        # Signal 1.1: Close vs SMA 20
        dist_sma20 = ((close - sma_20) / sma_20) * 100.0
        if dist_sma20 > 0.1:
            dir_20 = "bullish"
            score_20 = 1.0
            expl_20 = f"Price (INR {close:.2f}) trades {dist_sma20:+.2f}% above 20-SMA (INR {sma_20:.2f}), confirming positive short-term price position."
        elif dist_sma20 < -0.1:
            dir_20 = "bearish"
            score_20 = -1.0
            expl_20 = f"Price (INR {close:.2f}) trades {dist_sma20:+.2f}% below 20-SMA (INR {sma_20:.2f}), reflecting short-term price weakness."
        else:
            dir_20 = "neutral"
            score_20 = 0.0
            expl_20 = f"Price (INR {close:.2f}) is hovering directly at 20-SMA (INR {sma_20:.2f})."

        signals.append(
            DeterministicSignal(
                signal_id="close_vs_sma20",
                name="Price vs 20-Session SMA",
                category="price_position",
                direction=dir_20,
                numerical_observation=round(dist_sma20, 2),
                display_value=f"Close: INR {close:.2f} vs SMA-20: INR {sma_20:.2f} ({dist_sma20:+.2f}%)",
                rule_threshold="Close > SMA 20 (+0.1%) | Close < SMA 20 (-0.1%)",
                explanation=expl_20,
                evidence_ref=f"Close={close:.2f}, SMA20={sma_20:.2f}",
                is_valid=True,
            )
        )
        price_position_scores.append(score_20)

        # Signal 1.2: Close vs SMA 50
        if sma_50 is not None:
            dist_sma50 = ((close - sma_50) / sma_50) * 100.0
            if dist_sma50 > 0.1:
                dir_50 = "bullish"
                score_50 = 1.0
                expl_50 = f"Price (INR {close:.2f}) trades {dist_sma50:+.2f}% above 50-SMA (INR {sma_50:.2f}), indicating intermediate structural support."
            elif dist_sma50 < -0.1:
                dir_50 = "bearish"
                score_50 = -1.0
                expl_50 = f"Price (INR {close:.2f}) trades {dist_sma50:+.2f}% below 50-SMA (INR {sma_50:.2f}), indicating intermediate overhead resistance."
            else:
                dir_50 = "neutral"
                score_50 = 0.0
                expl_50 = f"Price (INR {close:.2f}) is hovering directly at 50-SMA (INR {sma_50:.2f})."

            signals.append(
                DeterministicSignal(
                    signal_id="close_vs_sma50",
                    name="Price vs 50-Session SMA",
                    category="price_position",
                    direction=dir_50,
                    numerical_observation=round(dist_sma50, 2),
                    display_value=f"Close: INR {close:.2f} vs SMA-50: INR {sma_50:.2f} ({dist_sma50:+.2f}%)",
                    rule_threshold="Close > SMA 50 (+0.1%) | Close < SMA 50 (-0.1%)",
                    explanation=expl_50,
                    evidence_ref=f"Close={close:.2f}, SMA50={sma_50:.2f}",
                    is_valid=True,
                )
            )
            price_position_scores.append(score_50)
        else:
            signals.append(
                DeterministicSignal(
                    signal_id="close_vs_sma50",
                    name="Price vs 50-Session SMA",
                    category="price_position",
                    direction="unavailable",
                    numerical_observation=None,
                    display_value="Unavailable (< 50 sessions)",
                    rule_threshold="Requires 50 trading sessions",
                    explanation=f"Dataset contains {total_sessions} sessions; 50-SMA cannot be calculated.",
                    evidence_ref="SMA50=None",
                    is_valid=False,
                )
            )

        cat_price_position = sum(price_position_scores) / len(price_position_scores)

        # -------------------------------------------------------------------------
        # Category 2: Trend Alignment (SMA-20 vs SMA-50 & SMA-20 Slope)
        # -------------------------------------------------------------------------
        trend_scores: List[float] = []

        # Signal 2.1: SMA 20 vs SMA 50
        if sma_50 is not None:
            if sma_20 > sma_50:
                dir_align = "bullish"
                score_align = 1.0
                expl_align = f"SMA-20 (INR {sma_20:.2f}) is above SMA-50 (INR {sma_50:.2f}), showing positive moving-average alignment."
            elif sma_20 < sma_50:
                dir_align = "bearish"
                score_align = -1.0
                expl_align = f"SMA-20 (INR {sma_20:.2f}) is below SMA-50 (INR {sma_50:.2f}), showing negative moving-average alignment."
            else:
                dir_align = "neutral"
                score_align = 0.0
                expl_align = "SMA-20 and SMA-50 are equal."

            signals.append(
                DeterministicSignal(
                    signal_id="sma20_vs_sma50",
                    name="Moving Average Alignment (20 vs 50)",
                    category="trend_alignment",
                    direction=dir_align,
                    numerical_observation=round(sma_20 - sma_50, 2),
                    display_value=f"SMA-20: INR {sma_20:.2f} vs SMA-50: INR {sma_50:.2f}",
                    rule_threshold="SMA 20 > SMA 50 (Bullish) | SMA 20 < SMA 50 (Bearish)",
                    explanation=expl_align,
                    evidence_ref=f"SMA20={sma_20:.2f}, SMA50={sma_50:.2f}",
                    is_valid=True,
                )
            )
            trend_scores.append(score_align)
        else:
            signals.append(
                DeterministicSignal(
                    signal_id="sma20_vs_sma50",
                    name="Moving Average Alignment (20 vs 50)",
                    category="trend_alignment",
                    direction="unavailable",
                    numerical_observation=None,
                    display_value="Unavailable (< 50 sessions)",
                    rule_threshold="Requires 50 trading sessions",
                    explanation="Intermediate moving average alignment unavailable due to insufficient historical bars.",
                    evidence_ref="SMA50=None",
                    is_valid=False,
                )
            )

        # Signal 2.2: SMA 20 Slope (5 sessions)
        slope_20 = indicator_summary.sma_20_slope_5d
        if slope_20 is not None:
            if slope_20 > 0.2:
                dir_slope = "bullish"
                score_slope = 0.5
                expl_slope = f"20-SMA is rising (+{slope_20:.2f}% over 5 sessions), indicating accelerating short-term trend."
            elif slope_20 < -0.2:
                dir_slope = "bearish"
                score_slope = -0.5
                expl_slope = f"20-SMA is declining ({slope_20:.2f}% over 5 sessions), indicating decelerating short-term trend."
            else:
                dir_slope = "neutral"
                score_slope = 0.0
                expl_slope = f"20-SMA is flat ({slope_20:+.2f}% over 5 sessions)."

            signals.append(
                DeterministicSignal(
                    signal_id="sma20_slope_5d",
                    name="20-Session SMA 5-Day Slope",
                    category="trend_alignment",
                    direction=dir_slope,
                    numerical_observation=round(slope_20, 2),
                    display_value=f"{slope_20:+.2f}% over 5 sessions",
                    rule_threshold="Slope > +0.2% (Rising) | Slope < -0.2% (Declining)",
                    explanation=expl_slope,
                    evidence_ref=f"SMA20_Slope_5d={slope_20:.2f}%",
                    is_valid=True,
                )
            )
            trend_scores.append(score_slope)

        cat_trend = (sum(trend_scores) / len(trend_scores)) if trend_scores else 0.0

        # -------------------------------------------------------------------------
        # Category 3: Momentum (RSI-14 and Latest Session Return)
        # -------------------------------------------------------------------------
        momentum_scores: List[float] = []

        # Signal 3.1: Latest Session Return (Explicitly single-session!)
        if daily_ret is not None:
            if daily_ret > 1.0:
                dir_ret = "bullish"
                score_ret = 0.5
                expl_ret = f"Latest session produced a strong positive return of {daily_ret:+.2f}% (single-session evidence only, does not establish a trend)."
            elif daily_ret < -1.0:
                dir_ret = "bearish"
                score_ret = -0.5
                expl_ret = f"Latest session produced a negative return of {daily_ret:+.2f}% (single-session evidence only, does not establish a trend)."
            else:
                dir_ret = "neutral"
                score_ret = 0.0
                expl_ret = f"Latest session return was moderate at {daily_ret:+.2f}%."

            signals.append(
                DeterministicSignal(
                    signal_id="latest_daily_return",
                    name="Latest Session Daily Return",
                    category="momentum",
                    direction=dir_ret,
                    numerical_observation=round(daily_ret, 2),
                    display_value=f"{daily_ret:+.2f}%",
                    rule_threshold="Return > +1.0% (Single-session Positive) | < -1.0% (Single-session Negative)",
                    explanation=expl_ret,
                    evidence_ref=f"DailyReturn={daily_ret:.2f}%",
                    is_valid=True,
                )
            )
            momentum_scores.append(score_ret)

        # Signal 3.2: 14-Session RSI
        if rsi is not None:
            if rsi > 70.0:
                dir_rsi = "neutral"
                score_rsi = 0.25
                expl_rsi = f"14-session RSI is elevated at {rsi:.2f} (> 70.0), indicating overbought momentum conditions."
                risk_factors.append(f"RSI-14 is overbought at {rsi:.2f}, indicating potential exhaustion or pullback risk.")
            elif rsi > 52.0:
                dir_rsi = "bullish"
                score_rsi = 1.0
                expl_rsi = f"14-session RSI is {rsi:.2f} (52.0 - 70.0), confirming constructive bullish momentum."
            elif rsi >= 48.0:
                dir_rsi = "neutral"
                score_rsi = 0.0
                expl_rsi = f"14-session RSI is neutral at {rsi:.2f} (midline zone 48.0 - 52.0)."
            elif rsi >= 30.0:
                dir_rsi = "bearish"
                score_rsi = -1.0
                expl_rsi = f"14-session RSI is {rsi:.2f} (30.0 - 48.0), reflecting weak/bearish momentum."
            else:
                dir_rsi = "neutral"
                score_rsi = -0.25
                expl_rsi = f"14-session RSI is deeply oversold at {rsi:.2f} (< 30.0)."
                risk_factors.append(f"RSI-14 is deeply oversold at {rsi:.2f}, reflecting heavy selling pressure.")

            signals.append(
                DeterministicSignal(
                    signal_id="rsi_14",
                    name="14-Session Relative Strength Index",
                    category="momentum",
                    direction=dir_rsi,
                    numerical_observation=round(rsi, 2),
                    display_value=f"{rsi:.2f}",
                    rule_threshold="50-70 (Bullish Momentum) | 30-50 (Bearish Momentum) | >70 (Overbought) | <30 (Oversold)",
                    explanation=expl_rsi,
                    evidence_ref=f"RSI14={rsi:.2f}",
                    is_valid=True,
                )
            )
            momentum_scores.append(score_rsi)
        else:
            signals.append(
                DeterministicSignal(
                    signal_id="rsi_14",
                    name="14-Session Relative Strength Index",
                    category="momentum",
                    direction="unavailable",
                    numerical_observation=None,
                    display_value="Unavailable (< 15 sessions)",
                    rule_threshold="Requires 15 trading sessions",
                    explanation="14-session RSI unavailable due to limited history.",
                    evidence_ref="RSI14=None",
                    is_valid=False,
                )
            )

        cat_momentum = (sum(momentum_scores) / len(momentum_scores)) if momentum_scores else 0.0

        # -------------------------------------------------------------------------
        # Category 4: Volume Confirmation
        # -------------------------------------------------------------------------
        volume_scores: List[float] = []
        if rel_vol is not None and price_summary.latest_volume > 0:
            if rel_vol >= 1.2:
                if daily_ret is not None and daily_ret > 0:
                    dir_vol = "bullish"
                    score_vol = 1.0
                    expl_vol = f"Traded volume ({price_summary.latest_volume:,}) was {rel_vol:.2f}x the 20-session average on an up-session, confirming buying participation."
                elif daily_ret is not None and daily_ret < 0:
                    dir_vol = "bearish"
                    score_vol = -1.0
                    expl_vol = f"Traded volume ({price_summary.latest_volume:,}) was {rel_vol:.2f}x the 20-session average on a down-session, confirming selling distribution."
                else:
                    dir_vol = "neutral"
                    score_vol = 0.0
                    expl_vol = f"Traded volume was elevated at {rel_vol:.2f}x average with flat price action."
            elif rel_vol <= 0.8:
                dir_vol = "neutral"
                score_vol = 0.0
                expl_vol = f"Traded volume was below average ({rel_vol:.2f}x 20-SMA volume), indicating low institutional conviction."
            else:
                dir_vol = "neutral"
                score_vol = 0.0
                expl_vol = f"Traded volume ({rel_vol:.2f}x average) is consistent with typical 20-session baseline."

            signals.append(
                DeterministicSignal(
                    signal_id="relative_volume",
                    name="Relative Volume (vs 20-Day Average)",
                    category="volume",
                    direction=dir_vol,
                    numerical_observation=round(rel_vol, 2),
                    display_value=f"{rel_vol:.2f}x ({price_summary.latest_volume:,} vs avg {price_summary.average_volume_20:,.0f})" if price_summary.average_volume_20 else f"{rel_vol:.2f}x",
                    rule_threshold="RelVol >= 1.2x with price gain (Bullish Accumulation) | RelVol >= 1.2x with price loss (Bearish Distribution)",
                    explanation=expl_vol,
                    evidence_ref=f"Volume={price_summary.latest_volume}, RelVol={rel_vol:.2f}",
                    is_valid=True,
                )
            )
            volume_scores.append(score_vol)
        else:
            signals.append(
                DeterministicSignal(
                    signal_id="relative_volume",
                    name="Relative Volume (vs 20-Day Average)",
                    category="volume",
                    direction="unavailable",
                    numerical_observation=None,
                    display_value="Unavailable (Requires 20 volume bars)",
                    rule_threshold="Requires 20 trading sessions with valid volume",
                    explanation="Volume comparison unavailable due to insufficient volume data.",
                    evidence_ref="RelVol=None",
                    is_valid=False,
                )
            )

        cat_volume = (sum(volume_scores) / len(volume_scores)) if volume_scores else 0.0

        # -------------------------------------------------------------------------
        # Risk Evaluation: Volatility Qualifier (Never shifts directional classification alone)
        # -------------------------------------------------------------------------
        if vol_ann is not None:
            if vol_ann >= 35.0:
                risk_factors.append(
                    f"Annualized 20-session historical volatility is elevated at {vol_ann:.2f}%, indicating significant price dispersion and drawdown potential."
                )
            elif vol_ann >= 20.0:
                risk_factors.append(
                    f"Annualized 20-session historical volatility is moderate at {vol_ann:.2f}%."
                )
        else:
            risk_factors.append("20-session annualized historical volatility unavailable (< 21 sessions).")

        # -------------------------------------------------------------------------
        # Category Aggregation and Authoritative Conflict Resolution
        # -------------------------------------------------------------------------
        # Weighted aggregate score
        active_weights = {}
        active_weights["price_position"] = cls.CATEGORY_WEIGHTS["price_position"]
        if trend_scores:
            active_weights["trend_alignment"] = cls.CATEGORY_WEIGHTS["trend_alignment"]
        if momentum_scores:
            active_weights["momentum"] = cls.CATEGORY_WEIGHTS["momentum"]
        if volume_scores:
            active_weights["volume"] = cls.CATEGORY_WEIGHTS["volume"]

        total_weight = sum(active_weights.values())
        raw_score = (
            (cat_price_position * active_weights["price_position"])
            + (cat_trend * active_weights.get("trend_alignment", 0.0))
            + (cat_momentum * active_weights.get("momentum", 0.0))
            + (cat_volume * active_weights.get("volume", 0.0))
        ) / total_weight

        aggregated_score = round(raw_score, 3)

        # Time-Horizon Conflict Detection:
        # e.g. TCS case: Price position is bullish (Close > SMA20 and Close > SMA50),
        # but Trend Alignment is bearish (SMA20 < SMA50).
        is_price_position_bullish = cat_price_position > 0.0
        is_trend_alignment_bearish = cat_trend < 0.0
        is_price_position_bearish = cat_price_position < 0.0
        is_trend_alignment_bullish = cat_trend > 0.0

        has_horizon_conflict = (
            (is_price_position_bullish and is_trend_alignment_bearish)
            or (is_price_position_bearish and is_trend_alignment_bullish)
        )

        if has_horizon_conflict:
            classification = "Mixed / Neutral"
            if is_price_position_bullish and is_trend_alignment_bearish:
                rationale = (
                    f"Score: {aggregated_score:+.2f}. Conflicting time horizons: Price (INR {close:.2f}) trades above both "
                    f"20-SMA and 50-SMA (short-term recovery), but 20-SMA remains below 50-SMA (intermediate bearish alignment). "
                    "Evidence is mixed and reconciled as Mixed / Neutral."
                )
            else:
                rationale = (
                    f"Score: {aggregated_score:+.2f}. Conflicting time horizons: Price trades below moving averages (short-term weakness), "
                    "while intermediate moving average alignment remains positive. Reconciled as Mixed / Neutral."
                )
        else:
            if aggregated_score >= 0.35:
                classification = "Bullish"
                rationale = f"Score: {aggregated_score:+.2f} (>= +0.35). Harmonious bullish evidence across price position and indicators."
            elif aggregated_score <= -0.35:
                classification = "Bearish"
                rationale = f"Score: {aggregated_score:+.2f} (<= -0.35). Harmonious bearish evidence across price position and indicators."
            else:
                classification = "Mixed / Neutral"
                rationale = f"Score: {aggregated_score:+.2f} (-0.35 to +0.35). Balanced or indecisive technical evidence."

        # Short-term and Medium-term Descriptive Summaries
        if close >= sma_20:
            st_action = f"Constructive: Trading {dist_sma20:+.2f}% above 20-SMA"
            if daily_ret is not None:
                st_action += f" with latest return of {daily_ret:+.2f}%"
        else:
            st_action = f"Depressed: Trading {dist_sma20:+.2f}% below 20-SMA"
            if daily_ret is not None:
                st_action += f" with latest return of {daily_ret:+.2f}%"

        if sma_50 is not None:
            if sma_20 > sma_50:
                mt_trend = "Bullish Alignment (20-SMA > 50-SMA, Golden Cross)"
            elif sma_20 < sma_50:
                mt_trend = "Bearish Alignment (20-SMA < 50-SMA, Death Cross)"
            else:
                mt_trend = "Neutral Alignment (20-SMA == 50-SMA)"
        else:
            mt_trend = "Unconfirmed (Requires 50 sessions for intermediate SMA)"

        return (
            classification,
            aggregated_score,
            rationale,
            signals,
            st_action,
            mt_trend,
            risk_factors,
        )
