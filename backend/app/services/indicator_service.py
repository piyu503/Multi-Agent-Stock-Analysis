"""Deterministic financial indicator calculator.

Conventions & Mathematical Specifications:
------------------------------------------
1. Daily Percentage Return:
   Return_t = ((Close_t / Close_{t-1}) - 1) * 100
   - Computed on the raw closing price series (default: "Close").
   - At t = 0 (first session), Return_0 is None / NaN because no prior session exists.

2. Simple Moving Average (SMA-N):
   SMA_N(t) = (1 / N) * sum_{i=0}^{N-1} Close_{t-i}
   - Rolling arithmetic mean over N trading sessions.
   - Requires exactly N non-null observations (min_periods=N).
   - If history has < N sessions, returns None.

3. 20-Session Annualized Historical Volatility:
   sigma_ann = std(Daily_Returns_pct, ddof=1) * sqrt(252)
   - Sample standard deviation (ddof=1) of 20 consecutive daily percentage returns.
   - Scaled by the square root of 252 trading sessions per calendar year.
   - Minimum Data Requirement: Because the first price session produces no return (Return_0 is NaN),
     20 daily returns requires exactly 21 consecutive trading sessions.
   - If fewer than 20 non-null return observations are present (i.e. < 21 price sessions),
     volatility is None.

4. Data Integrity:
   - All calculations are strictly deterministic and independent of any LLM.
   - Never fabricates, forward-fills, or interpolates missing prices.
"""

import math
from typing import List, Optional, Tuple
import pandas as pd

from app.schemas.market_data import IndicatorSeries, IndicatorSummary


class TechnicalIndicatorCalculator:
    """Computes deterministic indicators over a validated daily price series."""

    TRADING_DAYS_PER_YEAR: int = 252

    @classmethod
    def calculate(
        cls,
        df: pd.DataFrame,
        close_column: str = "Close",
    ) -> Tuple[List[IndicatorSeries], IndicatorSummary]:
        """Compute daily indicators and generate summary metrics.

        Args:
            df: Validated DataFrame with DatetimeIndex and target close column.
            close_column: Name of the closing price column to use (default: "Close").

        Returns:
            Tuple[List[IndicatorSeries], IndicatorSummary]: Chronological series and snapshot summary.
        """
        if df.empty or close_column not in df.columns:
            return [], IndicatorSummary()

        # Calculate daily percentage returns: (Close_t / Close_{t-1} - 1) * 100
        returns_pct = df[close_column].pct_change() * 100.0

        # 20-session and 50-session SMAs on target close column
        sma_20 = df[close_column].rolling(window=20, min_periods=20).mean()
        sma_50 = df[close_column].rolling(window=50, min_periods=50).mean()

        # 20-session rolling annualized volatility:
        # Standard deviation of percentage returns over 20 daily return values * sqrt(252)
        rolling_std_20 = returns_pct.rolling(window=20, min_periods=20).std(ddof=1)
        annualized_vol_20 = rolling_std_20 * math.sqrt(cls.TRADING_DAYS_PER_YEAR)

        # 14-session Relative Strength Index (Wilder's RSI)
        # delta = close_t - close_{t-1}; gain = max(delta, 0), loss = max(-delta, 0)
        # min_periods=14 ensures exactly 14 return periods (15 price bars)
        delta = df[close_column].diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0.0, float("nan"))
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        # Handle boundary conditions where avg_loss is 0
        rsi_series = rsi_series.where(~((avg_loss == 0.0) & (avg_gain > 0.0)), 100.0)
        rsi_series = rsi_series.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)

        # 20-session volume average and relative volume
        has_volume = "Volume" in df.columns and (df["Volume"] > 0).any()
        if has_volume:
            vol_sma_20 = df["Volume"].rolling(window=20, min_periods=20).mean()
            rel_vol = df["Volume"] / vol_sma_20.replace(0.0, float("nan"))
        else:
            vol_sma_20 = pd.Series(index=df.index, dtype=float)
            rel_vol = pd.Series(index=df.index, dtype=float)

        # 5-session slopes for SMAs: ((SMA_t - SMA_{t-4}) / SMA_{t-4}) * 100
        sma_20_slope = ((sma_20 - sma_20.shift(4)) / sma_20.shift(4)) * 100.0
        sma_50_slope = ((sma_50 - sma_50.shift(4)) / sma_50.shift(4)) * 100.0

        # Percentage distance from Close to SMAs
        dist_sma_20 = ((df[close_column] - sma_20) / sma_20) * 100.0
        dist_sma_50 = ((df[close_column] - sma_50) / sma_50) * 100.0

        series_list: List[IndicatorSeries] = []
        for idx in df.index:
            date_str = idx.strftime("%Y-%m-%d")
            ret_val = returns_pct.loc[idx]
            s20_val = sma_20.loc[idx]
            s50_val = sma_50.loc[idx]
            vol_val = annualized_vol_20.loc[idx]
            rsi_val = rsi_series.loc[idx]
            vsma_val = vol_sma_20.loc[idx]
            rvol_val = rel_vol.loc[idx]

            series_list.append(
                IndicatorSeries(
                    date=date_str,
                    daily_return_pct=round(float(ret_val), 4) if pd.notna(ret_val) else None,
                    sma_20=round(float(s20_val), 2) if pd.notna(s20_val) else None,
                    sma_50=round(float(s50_val), 2) if pd.notna(s50_val) else None,
                    volatility_20_annualized_pct=round(float(vol_val), 2) if pd.notna(vol_val) else None,
                    rsi_14=round(float(rsi_val), 2) if pd.notna(rsi_val) else None,
                    volume_sma_20=round(float(vsma_val), 2) if pd.notna(vsma_val) else None,
                    relative_volume=round(float(rvol_val), 2) if pd.notna(rvol_val) else None,
                )
            )

        # Build latest snapshot summary
        latest_idx = df.index[-1]
        latest_ret = returns_pct.loc[latest_idx]
        latest_s20 = sma_20.loc[latest_idx]
        latest_s50 = sma_50.loc[latest_idx]
        latest_vol = annualized_vol_20.loc[latest_idx]
        latest_rsi = rsi_series.loc[latest_idx]
        latest_vsma = vol_sma_20.loc[latest_idx]
        latest_rvol = rel_vol.loc[latest_idx]
        latest_dist20 = dist_sma_20.loc[latest_idx]
        latest_dist50 = dist_sma_50.loc[latest_idx]
        latest_slope20 = sma_20_slope.loc[latest_idx]
        latest_slope50 = sma_50_slope.loc[latest_idx]

        trend = "insufficient_data"
        if pd.notna(latest_s20) and pd.notna(latest_s50):
            trend = "bullish" if latest_s20 > latest_s50 else "bearish"

        summary = IndicatorSummary(
            latest_daily_return_pct=round(float(latest_ret), 4) if pd.notna(latest_ret) else None,
            latest_sma_20=round(float(latest_s20), 2) if pd.notna(latest_s20) else None,
            latest_sma_50=round(float(latest_s50), 2) if pd.notna(latest_s50) else None,
            latest_volatility_20_annualized_pct=round(float(latest_vol), 2) if pd.notna(latest_vol) else None,
            trend_20_vs_50=trend,
            latest_rsi_14=round(float(latest_rsi), 2) if pd.notna(latest_rsi) else None,
            latest_volume_sma_20=round(float(latest_vsma), 2) if pd.notna(latest_vsma) else None,
            latest_relative_volume=round(float(latest_rvol), 2) if pd.notna(latest_rvol) else None,
            close_vs_sma_20_pct=round(float(latest_dist20), 2) if pd.notna(latest_dist20) else None,
            close_vs_sma_50_pct=round(float(latest_dist50), 2) if pd.notna(latest_dist50) else None,
            sma_20_slope_5d=round(float(latest_slope20), 2) if pd.notna(latest_slope20) else None,
            sma_50_slope_5d=round(float(latest_slope50), 2) if pd.notna(latest_slope50) else None,
        )

        return series_list, summary
