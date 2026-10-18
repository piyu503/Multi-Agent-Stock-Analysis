"""Comprehensive unit and regression tests for MarketDataValidator, TechnicalIndicatorCalculator, and API endpoints."""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pandas as pd
import pytest
from httpx import AsyncClient

from app.schemas.market_data import ValidationSeverity, ValidationStatus
from app.services.indicator_service import TechnicalIndicatorCalculator
from app.services.market_data_service import MarketDataService
from app.services.market_data_validator import MarketDataValidator


def create_sample_ohlcv(
    days: int = 60,
    start_date: str = "2026-07-01",
    base_price: float = 3000.0,
    daily_increment: float = 5.0,
) -> pd.DataFrame:
    """Helper to generate a clean synthetic daily OHLCV dataframe."""
    date_range = pd.date_range(start=start_date, periods=days, freq="B")  # Business days
    data = []
    current_price = base_price
    for _ in range(len(date_range)):
        o = current_price
        h = current_price + 25.0
        l = current_price - 15.0
        c = current_price + daily_increment
        v = 1500000
        data.append({
            "Open": o,
            "High": h,
            "Low": l,
            "Close": c,
            "Adj Close": c,
            "Volume": v,
        })
        current_price = c

    df = pd.DataFrame(data, index=date_range)
    return df


class TestTimezoneAndDatePreservation:
    """Regression tests verifying timezone handling and date normalization."""

    def test_indian_standard_time_midnight_does_not_shift_to_sunday(self):
        """CRITICAL REGRESSION:

        When yfinance returns NSE timestamps with Asia/Kolkata timezone (e.g. '2026-10-12 00:00:00+05:30', Monday),
        the validator must preserve Monday '2026-10-12' and NOT shift to Sunday '2026-10-11' via UTC conversion.
        """
        tz_index = pd.DatetimeIndex([
            "2026-10-09 00:00:00+05:30",  # Friday
            "2026-10-12 00:00:00+05:30",  # Monday
            "2026-10-13 00:00:00+05:30",  # Tuesday
        ])
        df = pd.DataFrame(
            {
                "Open": [100.0, 102.0, 104.0],
                "High": [105.0, 106.0, 108.0],
                "Low": [98.0, 100.0, 102.0],
                "Close": [102.0, 104.0, 106.0],
                "Adj Close": [102.0, 104.0, 106.0],
                "Volume": [1000, 1200, 1100],
            },
            index=tz_index,
        )

        result, cleaned_df = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")

        assert result.status == ValidationStatus.VALID
        formatted_dates = [d.strftime("%Y-%m-%d") for d in cleaned_df.index]
        days_of_week = [d.strftime("%A") for d in cleaned_df.index]

        assert formatted_dates == ["2026-10-09", "2026-10-12", "2026-10-13"]
        assert days_of_week == ["Friday", "Monday", "Tuesday"]
        assert "Sunday" not in days_of_week
        assert "2026-10-11" not in formatted_dates


class TestMarketDataValidator:
    def test_empty_dataset_returns_invalid(self):
        empty_df = pd.DataFrame()
        result, df = MarketDataValidator.validate_ohlcv_dataframe(empty_df, "TCS.NS")
        assert result.status == ValidationStatus.INVALID
        assert result.errors_count == 1
        assert any(i.code == "EMPTY_DATASET" for i in result.issues)
        assert df.empty

    def test_duplicate_dates_are_detected_and_recorded_in_details(self):
        df = create_sample_ohlcv(days=10)
        dup_row = df.iloc[2:3]
        dup_date = df.index[2].strftime("%Y-%m-%d")
        df_with_dups = pd.concat([df.iloc[:3], dup_row, df.iloc[3:]])

        result, cleaned_df = MarketDataValidator.validate_ohlcv_dataframe(df_with_dups, "TCS.NS")
        dup_issue = next(i for i in result.issues if i.code == "DUPLICATE_DATES_DETECTED")
        assert dup_issue.details is not None
        assert dup_date in dup_issue.details["discarded_dates"]
        assert len(cleaned_df) == 10

    def test_invalid_ohlc_relationships_recorded_and_dropped(self):
        df = create_sample_ohlcv(days=10)
        corrupt_date = df.index[3].strftime("%Y-%m-%d")
        # Corrupt 4th row: High is lower than Low
        df.iloc[3, df.columns.get_loc("High")] = 100.0
        df.iloc[3, df.columns.get_loc("Low")] = 500.0

        result, cleaned_df = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")
        ohlc_issue = next(i for i in result.issues if i.code == "INVALID_OHLC_RELATIONSHIP")
        assert ohlc_issue.details is not None
        assert corrupt_date in ohlc_issue.details["discarded_dates"]
        assert len(cleaned_df) == 9

    def test_non_positive_prices_dropped_and_recorded(self):
        df = create_sample_ohlcv(days=10)
        corrupt_date = df.index[2].strftime("%Y-%m-%d")
        df.iloc[2, df.columns.get_loc("Close")] = -10.0

        result, cleaned_df = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")
        non_pos_issue = next(i for i in result.issues if i.code == "NON_POSITIVE_PRICE_DETECTED")
        assert non_pos_issue.details is not None
        assert corrupt_date in non_pos_issue.details["discarded_dates"]
        assert len(cleaned_df) == 9

    def test_missing_price_values_dropped_and_recorded(self):
        df = create_sample_ohlcv(days=10)
        corrupt_date = df.index[4].strftime("%Y-%m-%d")
        df.iloc[4, df.columns.get_loc("Open")] = float("nan")

        result, cleaned_df = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")
        nan_issue = next(i for i in result.issues if i.code == "MISSING_PRICE_VALUES")
        assert nan_issue.details is not None
        assert corrupt_date in nan_issue.details["discarded_dates"]
        assert len(cleaned_df) == 9

    def test_normal_weekend_is_not_flagged_as_gap(self):
        """Friday to Monday is 3 calendar days; must NOT trigger CALENDAR_GAP_WARNING."""
        dates = pd.date_range("2026-10-05", periods=5, freq="B")  # Mon to Fri
        df = create_sample_ohlcv(days=5, start_date="2026-10-05")
        result, _ = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")
        assert not any(i.code == "CALENDAR_GAP_WARNING" for i in result.issues)

    def test_calendar_gap_greater_than_7_days_is_flagged(self):
        """A gap of 10 days between trading sessions must be flagged."""
        df1 = create_sample_ohlcv(days=3, start_date="2026-09-01")
        df2 = create_sample_ohlcv(days=3, start_date="2026-09-15")  # 14-day gap
        df_gap = pd.concat([df1, df2])

        result, _ = MarketDataValidator.validate_ohlcv_dataframe(df_gap, "TCS.NS")
        assert any(i.code == "CALENDAR_GAP_WARNING" for i in result.issues)

    def test_corporate_action_split_and_dividend_detection(self):
        df = create_sample_ohlcv(days=10)
        df["Stock Splits"] = 0.0
        df["Dividends"] = 0.0
        df.iloc[3, df.columns.get_loc("Stock Splits")] = 2.0  # 2:1 split
        df.iloc[6, df.columns.get_loc("Dividends")] = 15.0  # 15 INR dividend

        result, _ = MarketDataValidator.validate_ohlcv_dataframe(df, "TCS.NS")
        assert any(i.code == "CORPORATE_ACTION_SPLIT_DETECTED" for i in result.issues)
        assert any(i.code == "DIVIDEND_EVENT_DETECTED" for i in result.issues)


class TestDeterministicIndicatorMath:
    """Hand-calculable mathematical verification for indicators."""

    def test_daily_return_hand_calculation(self):
        """Verify: (Close_t / Close_{t-1} - 1) * 100."""
        dates = pd.date_range("2026-10-01", periods=4, freq="B")
        df = pd.DataFrame(
            {
                "Open": [100.0, 105.0, 102.9, 108.0],
                "High": [105.0, 108.0, 106.0, 110.0],
                "Low": [98.0, 101.0, 100.0, 105.0],
                "Close": [100.0, 105.0, 102.9, 106.0],  # 100 -> 105 (+5%), 105 -> 102.9 (-2%), 102.9 -> 106 (+3.0126%)
            },
            index=dates,
        )

        series, summary = TechnicalIndicatorCalculator.calculate(df)

        assert len(series) == 4
        assert series[0].daily_return_pct is None  # Day 0: no previous session
        assert series[1].daily_return_pct == 5.0  # ((105 - 100) / 100) * 100 = 5.0%
        assert series[2].daily_return_pct == -2.0  # ((102.9 - 105) / 105) * 100 = -2.0%
        assert series[3].daily_return_pct == round(((106.0 / 102.9) - 1.0) * 100.0, 4)
        assert summary.latest_daily_return_pct == series[3].daily_return_pct

    def test_sma_20_and_sma_50_hand_calculation(self):
        """Verify exact rolling arithmetic mean on constant and sequential price series."""
        # 1. Constant price of 250.0 for 25 sessions
        dates = pd.date_range("2026-08-01", periods=25, freq="B")
        df_const = pd.DataFrame({"Close": [250.0] * 25}, index=dates)
        series, summary = TechnicalIndicatorCalculator.calculate(df_const)

        # Before 20th session (idx 0..18), sma_20 is None
        assert all(s.sma_20 is None for s in series[:19])
        # 20th session onwards (idx 19..24), sma_20 is exactly 250.0
        assert all(s.sma_20 == 250.0 for s in series[19:])
        assert summary.latest_sma_20 == 250.0
        # 25 sessions is < 50, so sma_50 is None
        assert summary.latest_sma_50 is None

        # 2. Linear prices: 1.0, 2.0, ..., 20.0
        # Mean of 1..20 is (1 + 20) / 2 = 10.5
        dates_linear = pd.date_range("2026-08-01", periods=20, freq="B")
        df_linear = pd.DataFrame({"Close": [float(i) for i in range(1, 21)]}, index=dates_linear)
        series_lin, summary_lin = TechnicalIndicatorCalculator.calculate(df_linear)
        assert summary_lin.latest_sma_20 == 10.5

    def test_volatility_20_session_hand_calculation_and_window_size(self):
        """Hand-calculable annualized volatility test:

        Mathematical specification:
        - Exactly 20 daily return values are required (sample size N = 20).
        - 20 daily returns requires 21 price sessions (Day 0 to Day 20).
        - Let prices produce alternating daily returns of +1.0% and -1.0% (10 of +1.0%, 10 of -1.0%).
          Mean return = 0.0.
          Sum of squared deviations = 20 * (1.0)^2 = 20.0.
          Sample variance (ddof=1) = 20.0 / (20 - 1) = 20 / 19 ≈ 1.05263158.
          Sample standard deviation = sqrt(20 / 19) ≈ 1.02597836.
          Annualized volatility = 1.02597836 * sqrt(252) ≈ 16.2869% (rounds to 16.29%).
        """
        # Case A: 20 price sessions produces only 19 returns -> Volatility MUST be None
        prices_20 = [100.0]
        for i in range(19):
            mult = 1.01 if i % 2 == 0 else 0.99
            prices_20.append(prices_20[-1] * mult)

        dates_20 = pd.date_range("2026-08-01", periods=20, freq="B")
        df_20 = pd.DataFrame({"Close": prices_20}, index=dates_20)
        _, summary_20 = TechnicalIndicatorCalculator.calculate(df_20)
        assert summary_20.latest_volatility_20_annualized_pct is None

        # Case B: 21 price sessions produces exactly 20 returns
        # Construct alternating exact returns: +1.0%, -1.0%, +1.0%, -1.0% ...
        prices_21 = [100.0]
        for i in range(20):
            # To get exact +1% return: P_t = P_{t-1} * 1.01
            # To get exact -1% return: P_t = P_{t-1} * 0.99
            factor = 1.01 if i % 2 == 0 else 0.99
            prices_21.append(prices_21[-1] * factor)

        dates_21 = pd.date_range("2026-08-01", periods=21, freq="B")
        df_21 = pd.DataFrame({"Close": prices_21}, index=dates_21)
        series_21, summary_21 = TechnicalIndicatorCalculator.calculate(df_21)

        # Expected volatility calculation:
        returns = df_21["Close"].pct_change().dropna()
        assert len(returns) == 20
        expected_std = returns.std(ddof=1)
        expected_vol = round(float(expected_std * 100.0 * math.sqrt(252)), 2)

        assert summary_21.latest_volatility_20_annualized_pct is not None
        assert summary_21.latest_volatility_20_annualized_pct == expected_vol


class TestMarketDataService:
    def test_symbol_resolution(self):
        assert MarketDataService.resolve_symbol("tcs") == "TCS.NS"
        assert MarketDataService.resolve_symbol("TCS.NS") == "TCS.NS"
        assert MarketDataService.resolve_symbol("infy") == "INFY.NS"
        assert MarketDataService.resolve_symbol("reliance.ns") == "RELIANCE.NS"
        assert MarketDataService.resolve_symbol("AAPL") == "AAPL.NS"  # Defaults to .NS if no dot
        assert MarketDataService.resolve_symbol("AAPL.US") == "AAPL.US"


@pytest.mark.asyncio
class TestMarketDataApi:
    async def test_api_endpoint_success_with_mocked_provider(self, client: AsyncClient):
        mock_df = create_sample_ohlcv(days=60)
        mock_info = {
            "name": "Tata Consultancy Services Limited",
            "currency": "INR",
            "exchange": "NSI",
            "sector": "Information Technology",
            "industry": "Information Technology Services",
        }

        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(mock_df, mock_info),
        ):
            resp = await client.get("/api/v1/market-data/TCS")
            assert resp.status_code == 200
            data = resp.json()

            assert data["requested_ticker"] == "TCS"
            assert data["provider_ticker"] == "TCS.NS"
            assert data["is_live_price"] is False
            assert data["price_series_convention"] == "raw_close"
            assert "Yahoo Finance" in data["provider"]
            assert data["company"]["name"] == "Tata Consultancy Services Limited"
            assert data["validation"]["status"] in ["valid", "warning"]
            assert len(data["price_history"]) == 60
            assert len(data["indicator_series"]) == 60
            assert data["indicators_summary"]["latest_sma_20"] is not None
            assert data["indicators_summary"]["latest_sma_50"] is not None

            # Verify consistency between latest fields and last bar
            latest_bar = data["price_history"][-1]
            assert data["latest_trading_date"] == latest_bar["date"]
            assert data["latest_close"] == latest_bar["close"]

    async def test_api_endpoint_not_found_on_empty_dataset(self, client: AsyncClient):
        with patch.object(
            MarketDataService,
            "_fetch_yfinance_data_sync",
            return_value=(pd.DataFrame(), {}),
        ):
            resp = await client.get("/api/v1/market-data/NONEXISTENT_TICKER_XYZ")
            assert resp.status_code == 404
            data = resp.json()
            assert "detail" in data
