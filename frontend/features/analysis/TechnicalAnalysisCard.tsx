'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { fetchTechnicalAnalysis } from '@/lib/api-client';
import { DeterministicSignal, TechnicalAnalysisResponse } from '@/types/technical-analysis';

const PERIOD_OPTIONS = [
  { label: '1 Month', value: '1mo' },
  { label: '3 Months', value: '3mo' },
  { label: '6 Months', value: '6mo' },
  { label: '1 Year', value: '1y' },
  { label: '2 Years', value: '2y' },
];

export function TechnicalAnalysisCard() {
  const [tickerInput, setTickerInput] = useState('TCS');
  const [period, setPeriod] = useState('6mo');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<TechnicalAnalysisResponse | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const handleRunAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tickerInput.trim()) return;

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const result = await fetchTechnicalAnalysis(tickerInput.trim().toUpperCase(), period);
      setAnalysis(result.data);
      setLatencyMs(result.latencyMs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Technical analysis execution failed';
      setErrorMsg(msg);
      setAnalysis(null);
    } finally {
      setIsLoading(false);
    }
  };

  const getClassificationBadge = (classification: string) => {
    switch (classification) {
      case 'Bullish':
        return <Badge variant="success">Bullish</Badge>;
      case 'Bearish':
        return <Badge variant="error">Bearish</Badge>;
      case 'Mixed / Neutral':
        return <Badge variant="warning">Mixed / Neutral</Badge>;
      default:
        return <Badge variant="neutral">Insufficient Data</Badge>;
    }
  };

  const getSignalDirectionBadge = (dir: DeterministicSignal['direction']) => {
    switch (dir) {
      case 'bullish':
        return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/60">+ Bullish</span>;
      case 'bearish':
        return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800/60">- Bearish</span>;
      case 'neutral':
        return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60">= Neutral</span>;
      default:
        return <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">∅ Unavailable</span>;
    }
  };

  return (
    <Card className="p-6 border-slate-800 bg-slate-900/50 backdrop-blur-sm space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-white">Technical Stock Analyst</h2>
            <span className="text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded">
              Audited Evidence Engine
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic Python signal evaluation combined with bounded local LLM (DeepSeek R1) synthesis.
          </p>
        </div>

        {/* Input Form */}
        <form onSubmit={handleRunAnalysis} className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            placeholder="e.g. TCS, INFY"
            className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono w-40 uppercase"
          />

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
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-4 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm shadow-indigo-600/30"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Evaluating Evidence...</span>
              </>
            ) : (
              <span>Run Technical Analysis</span>
            )}
          </button>
        </form>
      </div>

      {/* Provider & Model Transparency Banner */}
      <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 gap-2 font-mono">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Provider: <span className="text-white font-semibold">{analysis?.provider || 'ollama (local)'}</span>
          </span>
          <span className="text-slate-600">&bull;</span>
          <span>
            Model: <span className="text-indigo-300">{analysis?.model || 'deepseek-r1:7b'}</span>
          </span>
          {analysis && (
            <>
              <span className="text-slate-600">&bull;</span>
              <span>Data As-Of: <span className="text-emerald-400">{analysis.data_as_of}</span></span>
            </>
          )}
        </div>
        {latencyMs !== null && (
          <span className="text-slate-400 text-[11px]">Execution Latency: {latencyMs}ms</span>
        )}
      </div>

      {/* Error state */}
      {errorMsg && (
        <div className="p-4 rounded-lg bg-rose-950/50 border border-rose-800/60 text-rose-200 text-sm flex items-start gap-3">
          <div className="mt-0.5 text-rose-400 font-bold">✕</div>
          <div>
            <div className="font-semibold text-rose-300">Technical Analysis Error</div>
            <p className="text-xs text-rose-200/90 mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="py-12 flex flex-col items-center justify-center space-y-3 text-slate-400">
          <div className="h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-mono">Executing deterministic signal engine & Ollama DeepSeek R1 synthesis...</p>
        </div>
      )}

      {/* Analysis Results Display */}
      {analysis && !isLoading && (
        <div className="space-y-6">
          {/* Authoritative Classification Hero */}
          <div className="p-5 rounded-xl border border-slate-800 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono uppercase text-slate-400">Overall Classification:</span>
                {getClassificationBadge(analysis.deterministic_classification)}
                {analysis.classification_score !== null && analysis.classification_score !== undefined && (
                  <span className="text-xs font-mono bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                    Conviction Score: {analysis.classification_score > 0 ? `+${analysis.classification_score.toFixed(2)}` : analysis.classification_score.toFixed(2)}
                  </span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Python Authoritative Decision</span>
            </div>
            <p className="text-sm text-slate-200 font-sans leading-relaxed">
              {analysis.classification_rationale}
            </p>
          </div>

          {/* Time-Horizon Disaggregation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1.5">
              <div className="text-xs font-mono text-indigo-400 flex items-center justify-between">
                <span>Short-Term Price Action</span>
                <span className="text-[10px] text-slate-500">Daily Return & vs SMA-20</span>
              </div>
              <div className="text-sm font-semibold text-white pt-1">
                {analysis.short_term_price_action}
              </div>
              <p className="text-xs text-slate-400 pt-1">
                Reflects immediate market participation and price position relative to the 20-session baseline.
              </p>
            </div>

            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-1.5">
              <div className="text-xs font-mono text-purple-400 flex items-center justify-between">
                <span>Medium-Term Trend Structure</span>
                <span className="text-[10px] text-slate-500">SMA Alignment (20 vs 50)</span>
              </div>
              <div className="text-sm font-semibold text-white pt-1">
                {analysis.medium_term_trend}
              </div>
              <p className="text-xs text-slate-400 pt-1">
                Reflects structural trend orientation and moving-average crossover geometry over 50 sessions.
              </p>
            </div>
          </div>

          {/* Comprehensive Indicator Matrix */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Price Snapshot */}
            <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-slate-400 font-mono">Latest Close</span>
              <div className="text-base font-bold text-white font-mono">
                ₹{analysis.price_summary.latest_close.toFixed(2)}
              </div>
              <div className="text-xs text-slate-400">
                Daily: <span className={analysis.price_summary.latest_daily_return_pct && analysis.price_summary.latest_daily_return_pct > 0 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                  {analysis.price_summary.latest_daily_return_pct !== null && analysis.price_summary.latest_daily_return_pct !== undefined ? `${analysis.price_summary.latest_daily_return_pct > 0 ? '+' : ''}${analysis.price_summary.latest_daily_return_pct.toFixed(2)}%` : 'N/A'}
                </span>
              </div>
            </div>

            {/* 20-Day SMA */}
            <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-indigo-400 font-mono">20-Session SMA</span>
              <div className="text-base font-bold text-white font-mono">
                {analysis.indicator_summary.sma_20 !== null && analysis.indicator_summary.sma_20 !== undefined
                  ? `₹${analysis.indicator_summary.sma_20.toFixed(2)}`
                  : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">
                Dist: <span className="font-mono text-slate-200">
                  {analysis.indicator_summary.close_vs_sma_20_pct !== null && analysis.indicator_summary.close_vs_sma_20_pct !== undefined
                    ? `${analysis.indicator_summary.close_vs_sma_20_pct > 0 ? '+' : ''}${analysis.indicator_summary.close_vs_sma_20_pct.toFixed(2)}%`
                    : 'N/A'}
                </span>
              </div>
            </div>

            {/* 50-Day SMA */}
            <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-purple-400 font-mono">50-Session SMA</span>
              <div className="text-base font-bold text-white font-mono">
                {analysis.indicator_summary.sma_50 !== null && analysis.indicator_summary.sma_50 !== undefined
                  ? `₹${analysis.indicator_summary.sma_50.toFixed(2)}`
                  : 'Unavailable'}
              </div>
              <div className="text-xs text-slate-400">
                Dist: <span className="font-mono text-slate-200">
                  {analysis.indicator_summary.close_vs_sma_50_pct !== null && analysis.indicator_summary.close_vs_sma_50_pct !== undefined
                    ? `${analysis.indicator_summary.close_vs_sma_50_pct > 0 ? '+' : ''}${analysis.indicator_summary.close_vs_sma_50_pct.toFixed(2)}%`
                    : 'N/A'}
                </span>
              </div>
            </div>

            {/* Momentum & Volatility */}
            <div className="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 space-y-1">
              <span className="text-[11px] text-amber-400 font-mono">RSI-14 / Volatility</span>
              <div className="text-sm font-bold text-white font-mono flex items-baseline gap-2">
                <span>RSI: {analysis.indicator_summary.rsi_14 !== null && analysis.indicator_summary.rsi_14 !== undefined ? analysis.indicator_summary.rsi_14.toFixed(1) : 'N/A'}</span>
              </div>
              <div className="text-xs text-slate-400">
                Vol: <span className="font-mono text-slate-200">
                  {analysis.indicator_summary.volatility_20_annualized_pct !== null && analysis.indicator_summary.volatility_20_annualized_pct !== undefined
                    ? `${analysis.indicator_summary.volatility_20_annualized_pct.toFixed(1)}%`
                    : 'N/A'}
                </span>
                {analysis.price_summary.relative_volume !== null && analysis.price_summary.relative_volume !== undefined && (
                  <span className="ml-1 text-[11px] text-indigo-300">({analysis.price_summary.relative_volume.toFixed(1)}x Vol)</span>
                )}
              </div>
            </div>
          </div>

          {/* Deterministic Signals Evidence Audit Table */}
          {analysis.deterministic_signals && analysis.deterministic_signals.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Deterministic Technical Signals
                </h3>
                <span className="text-[11px] text-slate-500 font-mono">Rule-Based Output</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {analysis.deterministic_signals.map((sig) => (
                  <div
                    key={sig.signal_id}
                    className="p-3 rounded-lg border border-slate-800/80 bg-slate-950/50 space-y-1.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-200">{sig.name}</span>
                      {getSignalDirectionBadge(sig.direction)}
                    </div>
                    <div className="text-[11px] font-mono text-indigo-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 inline-block">
                      {sig.display_value}
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">{sig.explanation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trend Interpretation Narrative */}
          <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
              Evidence-Grounded Interpretation
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">{analysis.trend_interpretation}</p>
          </div>

          {/* Bullish & Bearish Signals Columns */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Bullish Signals */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-emerald-950/60 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs uppercase tracking-wider">
                <Badge variant="success">Bullish Evidence</Badge>
              </div>
              {analysis.bullish_signals.length > 0 ? (
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {analysis.bullish_signals.map((sig, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-400 font-bold mt-0.5">+</span>
                      <span>{sig}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No verified bullish signals identified.</p>
              )}
            </div>

            {/* Bearish Signals */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-rose-950/60 space-y-2">
              <div className="flex items-center gap-2 text-rose-400 font-semibold text-xs uppercase tracking-wider">
                <Badge variant="error">Bearish / Warning Signs</Badge>
              </div>
              {analysis.bearish_signals.length > 0 ? (
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {analysis.bearish_signals.map((sig, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-rose-400 font-bold mt-0.5">-</span>
                      <span>{sig}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No verified bearish signals identified.</p>
              )}
            </div>
          </div>

          {/* Risk Factors & Uncertainties */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Risk Factors */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-2">
              <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <span>⚠</span> Risk Factors
              </h4>
              <ul className="space-y-1 text-xs text-slate-300">
                {analysis.risk_factors.map((rf, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-amber-400">&bull;</span>
                    <span>{rf}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Uncertainties & Data Limitations */}
            <div className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <span>?</span> Limitations & Missing Data
              </h4>
              <ul className="space-y-1 text-xs text-slate-400">
                {analysis.missing_data.map((md, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-slate-500">&bull;</span>
                    <span>{md}</span>
                  </li>
                ))}
                {analysis.uncertainties.map((unc, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-indigo-400">&bull;</span>
                    <span>{unc}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Conclusion & Compliance Disclaimer */}
          <div className="bg-indigo-950/20 p-5 rounded-xl border border-indigo-900/40 space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300">
              Analyst Synthesis & Conclusion
            </h4>
            <p className="text-sm text-slate-200 leading-relaxed font-sans">{analysis.conclusion}</p>
            <p className="text-[11px] text-slate-500 pt-2 border-t border-indigo-900/30 italic">
              {analysis.disclaimer}
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}
