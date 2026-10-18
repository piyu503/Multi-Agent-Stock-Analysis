"""Manual live smoke test for verifying real TCS.NS market data feed.

This script makes a real live outbound network request to Yahoo Finance.
Run manually when network access is verified:
    python scripts/smoke_test_market_data.py
"""

import asyncio
from app.services.market_data_service import MarketDataService


async def main():
    print("Executing live market data retrieval for TCS.NS...")
    result = await MarketDataService.get_daily_market_data("TCS", period="1mo")

    print(f"Requested: {result.requested_ticker}")
    print(f"Provider Symbol: {result.provider_ticker}")
    print(f"Provider: {result.provider}")
    print(f"Is Live Price: {result.is_live_price}")
    print(f"Company: {result.company.name} ({result.company.currency})")
    print(f"Latest Session: {result.latest_trading_date}")
    print(f"Latest Close: INR {result.latest_close}")
    print(f"Validation Status: {result.validation.status} (Warnings: {result.validation.warnings_count}, Errors: {result.validation.errors_count})")
    for issue in result.validation.issues:
        print(f"  - [{issue.severity.upper()}] {issue.code}: {issue.message}")

    print("Indicators Summary:")
    print(f"  - Daily Return: {result.indicators_summary.latest_daily_return_pct}%")
    print(f"  - 20-Day SMA: INR {result.indicators_summary.latest_sma_20}")
    print(f"  - 50-Day SMA: INR {result.indicators_summary.latest_sma_50}")
    print(f"  - 20-Day Volatility (Annualized): {result.indicators_summary.latest_volatility_20_annualized_pct}%")
    print(f"Total Bars Processed: {len(result.price_history)}")
    if result.price_history:
        latest = result.price_history[-1]
        print(f"Latest Bar: Date={latest.date}, O={latest.open}, H={latest.high}, L={latest.low}, C={latest.close}, Vol={latest.volume}")


if __name__ == "__main__":
    asyncio.run(main())
