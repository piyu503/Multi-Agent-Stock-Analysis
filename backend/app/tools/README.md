# Tools Subsystem

## Purpose
This directory will contain verified data ingestion adapters and deterministic calculation tools used by the analysis agents.

## Planned Tools
1. **SEC EDGAR Tool**: Fetches 10-K, 10-Q, 8-K filings and parses XBRL financial statements.
2. **Market Data Provider**: Connects to financial data APIs (e.g. Financial Modeling Prep, Polygon.io, or Yahoo Finance) for historical prices, volumes, and splits.
3. **News & Web Search Tool**: Real-time financial news searching with source credibility ranking and date filtering.
4. **Financial Calculation Engine**: Pure Python numerical calculations (DCF formulas, WACC estimation, Altman Z-score, Piotroski F-score) ensuring deterministic math without LLM arithmetic hallucinations.
5. **Citation & Source Verifier**: Cross-checks LLM generated numbers against raw SEC filings and reports exact source URLs.
