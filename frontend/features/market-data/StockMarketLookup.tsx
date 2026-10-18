'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { fetchMarketData } from '@/lib/api-client';
import { MarketDataResponse } from '@/types/market-data';

const PERIOD_OPTIONS = [
  { label: '1 Month', value: '1mo' },
  { label: '3 Months', value: '3mo' },
  { label: '6 Months', value: '6mo' },
  { label: '1 Year', value: '1y' },
  { label: '2 Years', value: '2y' },
];

export function StockMarketLookup() {
  const [tickerInput, setTickerInput] = useState('TCS');
  const [activeTicker, setActiveTicker] = useState('TCS');
  const [period, setPeriod] = useState('6mo');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [marketData, setMarketData] = useState<MarketDataResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  useEffect(() => {
    let isCancelled = false;

    async function executeFetch() {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const result = await fetchMarketData(activeTicker, period);
        if (!isCancelled) {
          setMarketData(result.data);
          setLatencyMs(result.latencyMs);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to retrieve market data';
          setErrorMsg(msg);
          setMarketData(null);
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    executeFetch();

    return () => {
      isCancelled = true;
    };
  }, [activeTicker, period]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tickerInput.trim()) {
      setActiveTicker(tickerInput.trim().toUpperCase());
    }
  };

  const getValidationBadge = (status?: string) => {
    switch (status) {
      case 'valid':
        return <Badge variant="success">Integrity: Valid</Badge>;
      case 'warning':
        return <Badge variant="warning">Integrity: Warnings</Badge>;
      case 'invalid':
        return <Badge variant="error">Integrity: Invalid</Badge>;
      default:
        return null;
    }
  };

  return (
    <Card className="p-6 border-slate-800 bg-slate-900/50 backdrop-blur-sm space-y-6">
      {/* Header and Lookup Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">NSE Equity Market Data Feed</h2>
            <span className="text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded">
              Milestone 1
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic daily OHLCV bars, integrity validation audit, and mathematical technical indicators.
          </p>
        </div>

        {/* Search & Period Selector */}
        <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <input
              type="text"
              value={tickerInput}
              onChange={(e) => setTickerInput(e.target.value)}
              placeholder="e.g. TCS, INFY, RELIANCE"
              className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono w-44 uppercase"
            />
          </div>

          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="bg-slate-950 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-sans"
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <button
            type="submit"
            disabled={isLoading || !tickerInput.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-3.5 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Fetching...</span>
              </>
            ) : (
              <span>Load Ticker</span>
            )}
          </button>
        </form>
      </div>

      {/* Disclaimers & Source attribution */}
      <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 gap-2 font-mono">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Provider: {marketData?.provider || 'yfinance (Daily Historical)'}
          </span>
          <span className="text-slate-600">&bull;</span>
          <span className="text-amber-400/90 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded text-[11px]">
            Daily EOD &bull; Not Live Intraday
          </span>
        </div>
        {latencyMs !== null && (
          <span className="text-slate-400 text-[11px]">API Roundtrip: {latencyMs}ms</span>
        )}
      </div>

      {/* Error state */}
      {errorMsg && (
        <div className="p-4 rounded-lg bg-rose-950/50 border border-rose-800/60 text-rose-200 text-sm flex items-start gap-3">
          <div className="mt-0.5 text-rose-400 font-bold">✕</div>
          <div>
            <div className="font-semibold text-rose-300">Data Retrieval Error</div>
            <p className="text-xs text-rose-200/90 mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && !marketData && (
        <div className="py-12 flex flex-col items-center justify-center space-y-3 text-slate-400">
          <div className="h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-mono">Connecting to provider and validating data series...</p>
        </div>
      )}

      {/* Data display */}
      {marketData && (
        <div className="space-y-6">
          {/* Company & Price Summary Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Ticker & Identity */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400">Symbol / Resolved</span>
                {getValidationBadge(marketData.validation.status)}
              </div>
              <div className="text-lg font-bold text-white tracking-tight flex items-baseline gap-2">
                <span>{marketData.requested_ticker}</span>
                <span className="text-xs font-mono text-indigo-400">({marketData.provider_ticker})</span>
              </div>
              <div className="text-xs text-slate-400 truncate">
                {marketData.company.name || 'NSE Equity'}
              </div>
              {marketData.company.sector && (
                <div className="text-[11px] text-slate-500 truncate">
                  {marketData.company.sector} &bull; {marketData.company.currency || 'INR'}
                </div>
              )}
            </div>

            {/* Latest Close */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-xs font-mono text-slate-400">Latest Session Close</span>
              <div className="text-2xl font-black text-white tracking-tight">
                {marketData.latest_close !== null && marketData.latest_close !== undefined
                  ? `₹${marketData.latest_close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                  : 'N/A'}
              </div>
              <div className="text-xs text-slate-400 flex items-center justify-between">
                <span>Date: {marketData.latest_trading_date || 'N/A'}</span>
                {marketData.indicators_summary.latest_daily_return_pct !== null &&
                  marketData.indicators_summary.latest_daily_return_pct !== undefined && (
                    <span
                      className={`font-mono text-xs font-semibold ${
                        marketData.indicators_summary.latest_daily_return_pct >= 0
                          ? 'text-emerald-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {marketData.indicators_summary.latest_daily_return_pct >= 0 ? '+' : ''}
                      {marketData.indicators_summary.latest_daily_return_pct}%
                    </span>
                  )}
              </div>
            </div>

            {/* 20-Day & 50-Day Moving Averages */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-xs font-mono text-slate-400">Simple Moving Averages</span>
              <div className="space-y-1 pt-0.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-indigo-400 font-medium">20-SMA:</span>
                  <span className="font-mono text-white">
                    {marketData.indicators_summary.latest_sma_20 !== null &&
                    marketData.indicators_summary.latest_sma_20 !== undefined
                      ? `₹${marketData.indicators_summary.latest_sma_20.toFixed(2)}`
                      : 'Insufficient (<20 bars)'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-purple-400 font-medium">50-SMA:</span>
                  <span className="font-mono text-white">
                    {marketData.indicators_summary.latest_sma_50 !== null &&
                    marketData.indicators_summary.latest_sma_50 !== undefined
                      ? `₹${marketData.indicators_summary.latest_sma_50.toFixed(2)}`
                      : 'Insufficient (<50 bars)'}
                  </span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 pt-1 border-t border-slate-800/60 flex justify-between">
                <span>Trend:</span>
                <span className="capitalize font-medium text-slate-300">
                  {marketData.indicators_summary.trend_20_vs_50?.replace('_', ' ') || 'N/A'}
                </span>
              </div>
            </div>

            {/* 20-Session Annualized Volatility */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-xs font-mono text-slate-400">Historical Volatility (20d)</span>
              <div className="text-2xl font-black text-white tracking-tight">
                {marketData.indicators_summary.latest_volatility_20_annualized_pct !== null &&
                marketData.indicators_summary.latest_volatility_20_annualized_pct !== undefined
                  ? `${marketData.indicators_summary.latest_volatility_20_annualized_pct}%`
                  : 'Insufficient (<21 bars)'}
              </div>
              <div className="text-[11px] text-slate-500">
                Annualized sample std (ddof=1, 20 returns / 21 sessions, sqrt(252))
              </div>
            </div>
          </div>

          {/* Validation Audit Logs / Warnings */}
          {marketData.validation.issues.length > 0 && (
            <div className="space-y-2 bg-slate-950/70 p-4 rounded-xl border border-slate-800/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  Dataset Integrity & Validation Audit ({marketData.validation.total_records} Bars Processed)
                </span>
                <span className="text-[11px] text-slate-400">
                  Warnings: {marketData.validation.warnings_count} &bull; Errors: {marketData.validation.errors_count}
                </span>
              </div>
              <div className="divide-y divide-slate-800/60 max-h-36 overflow-y-auto pr-1">
                {marketData.validation.issues.map((issue, idx) => (
                  <div key={idx} className="py-2 text-xs flex items-start gap-2">
                    <span
                      className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded shrink-0 ${
                        issue.severity === 'error'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : issue.severity === 'warning'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {issue.code}
                    </span>
                    <span className="text-slate-300">{issue.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Daily Price History Table (Last 10 sessions) */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div>
                <h3 className="text-sm font-semibold text-white">Recent Daily Sessions (Last 10 Days)</h3>
                <p className="text-[11px] text-slate-400">
                  OHLC reflect raw exchange prices. Close is used for SMA & Return calculations. Adj Close incorporates dividends & splits.
                </p>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {marketData.price_history.length} total bars loaded
              </span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-800/80">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-950/80 text-slate-400 font-mono border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Open</th>
                    <th className="py-2.5 px-3">High</th>
                    <th className="py-2.5 px-3">Low</th>
                    <th className="py-2.5 px-3">Close</th>
                    <th className="py-2.5 px-3">Adj Close</th>
                    <th className="py-2.5 px-3">Volume</th>
                    <th className="py-2.5 px-3">Daily Return</th>
                    <th className="py-2.5 px-3">20-SMA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 bg-slate-950/40 font-mono">
                  {marketData.price_history.slice(-10).reverse().map((bar) => {
                    const ind = marketData.indicator_series.find((i) => i.date === bar.date);
                    const ret = ind?.daily_return_pct;
                    return (
                      <tr key={bar.date} className="hover:bg-slate-900/60 transition-colors">
                        <td className="py-2.5 px-3 text-slate-300">{bar.date}</td>
                        <td className="py-2.5 px-3 text-slate-400">₹{bar.open.toFixed(2)}</td>
                        <td className="py-2.5 px-3 text-slate-400">₹{bar.high.toFixed(2)}</td>
                        <td className="py-2.5 px-3 text-slate-400">₹{bar.low.toFixed(2)}</td>
                        <td className="py-2.5 px-3 font-semibold text-white">₹{bar.close.toFixed(2)}</td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {bar.adj_close !== null && bar.adj_close !== undefined ? `₹${bar.adj_close.toFixed(2)}` : '—'}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">{bar.volume.toLocaleString('en-IN')}</td>
                        <td className="py-2.5 px-3">
                          {ret !== null && ret !== undefined ? (
                            <span className={ret >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                              {ret >= 0 ? '+' : ''}
                              {ret.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-indigo-300">
                          {ind?.sma_20 !== null && ind?.sma_20 !== undefined
                            ? `₹${ind.sma_20.toFixed(2)}`
                            : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
