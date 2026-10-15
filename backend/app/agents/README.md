# Agents Subsystem

## Purpose
This directory will contain specialized AI agents participating in the multi-agent stock analysis pipeline. Each agent embodies a distinct domain perspective and reasoning strategy.

## Planned Specialized Agents
1. **Research & News Agent**: Gathers recent 8-K/10-K filings, earnings call transcripts, and market news.
2. **Fundamentals Agent**: Computes DCF, valuation multiples (P/E, EV/EBITDA, P/FCF), balance sheet health, and debt metrics.
3. **Technical Analysis Agent**: Evaluates price action, trend indicators (EMA, RSI, MACD), support/resistance levels, and volume profiles.
4. **Bull Thesis Agent**: Synthesizes growth catalysts, competitive moats, market expansion opportunities, and upside scenarios.
5. **Bear / Red Team Agent**: Challenges assumptions, audits accounting risks, identifies competitive threats, and builds downside stress tests.
6. **Risk Management Agent**: Analyzes volatility, beta, sector concentration, drawdown scenarios, and portfolio impact.
7. **Synthesis & Reviewer Agent**: Weighs evidence from all prior agents, resolves conflicting signals, formats citations, and generates final investment memo.

## Model Provider Abstraction
Agents must not import LLM client SDKs directly. All model invocations route through the model-provider abstraction in `core/` to allow zero-downtime switching between Gemini 1.5/2.0 Pro, Claude, OpenAI, or local open-weights models.
