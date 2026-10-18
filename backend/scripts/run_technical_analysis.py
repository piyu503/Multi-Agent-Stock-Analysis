"""Manual script to test live technical analysis on real market data with local Ollama."""

import asyncio
from app.services.technical_analyst import TechnicalAnalystService


async def main():
    print("Initiating technical analysis for TCS using configured LLM provider...")
    service = TechnicalAnalystService()
    print(f"Provider: {service.provider.provider_name} | Model: {service.provider.model_name}")

    try:
        result = await service.analyze(ticker="TCS", period="6mo")
        print("\n=== TECHNICAL ANALYSIS RESULT ===")
        print(f"Ticker: {result.ticker} ({result.resolved_ticker})")
        print(f"Company: {result.company_name}")
        print(f"As of: {result.data_as_of} | Analyzed at: {result.analysis_timestamp}")
        print(f"Provider / Model: {result.provider} / {result.model}")
        print(f"\nAuthoritative Deterministic Classification: {result.deterministic_classification}")
        if result.classification_score is not None:
            print(f"Conviction Score: {result.classification_score:+.2f}")
        print(f"Rationale: {result.classification_rationale}")
        print(f"Short-Term Price Action: {result.short_term_price_action}")
        print(f"Medium-Term Trend: {result.medium_term_trend}")

        print("\nDeterministic Price Summary:")
        print(f"  Latest Close: INR {result.price_summary.latest_close:.2f}")
        print(f"  Previous Close: INR {result.price_summary.previous_close:.2f}" if result.price_summary.previous_close else "  Previous Close: N/A")
        print(f"  Latest Return: {result.price_summary.latest_daily_return_pct:+.2f}%" if result.price_summary.latest_daily_return_pct is not None else "  Latest Return: N/A")
        print(f"  Volume: {result.price_summary.latest_volume:,} (Rel Vol: {result.price_summary.relative_volume}x)" if result.price_summary.relative_volume else f"  Volume: {result.price_summary.latest_volume:,}")
        print(f"  Period High: INR {result.price_summary.period_high:.2f} | Period Low: INR {result.price_summary.period_low:.2f}")

        print("\nDeterministic Indicators:")
        print(f"  20-SMA: INR {result.indicator_summary.sma_20} (Close is {result.indicator_summary.close_vs_sma_20_pct:+.2f}%)" if result.indicator_summary.sma_20 else "  20-SMA: N/A")
        print(f"  50-SMA: INR {result.indicator_summary.sma_50} (Close is {result.indicator_summary.close_vs_sma_50_pct:+.2f}%)" if result.indicator_summary.sma_50 else "  50-SMA: N/A")
        print(f"  14-RSI: {result.indicator_summary.rsi_14}" if result.indicator_summary.rsi_14 else "  14-RSI: N/A")
        print(f"  20-Session Volatility (Ann): {result.indicator_summary.volatility_20_annualized_pct}%" if result.indicator_summary.volatility_20_annualized_pct else "  20-Session Volatility (Ann): N/A")
        print(f"  Trend Orientation: {result.indicator_summary.trend_20_vs_50}")

        print("\nDeterministic Signals Evaluated by Python:")
        for sig in result.deterministic_signals:
            print(f"  [{sig.direction.upper()}] {sig.name}: {sig.display_value} -> {sig.explanation}")

        print("\nBullish Signals:")
        for s in result.bullish_signals:
            print(f"  + {s}")

        print("\nBearish Signals:")
        for s in result.bearish_signals:
            print(f"  - {s}")

        print("\nTrend Interpretation:")
        print(f"  {result.trend_interpretation}")

        print("\nRisk Factors:")
        for r in result.risk_factors:
            print(f"  ! {r}")

        print("\nUncertainties:")
        for u in result.uncertainties:
            print(f"  ? {u}")

        print("\nMissing Data / Limitations:")
        for m in result.missing_data:
            print(f"  * {m}")

        print("\nEvidence:")
        for e in result.evidence:
            print(f"  # {e}")

        print("\nConclusion:")
        print(f"  {result.conclusion}")

    except Exception as e:
        print(f"\nExecution error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
