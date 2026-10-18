export interface DeterministicSignal {
  signal_id: string;
  name: string;
  category: 'price_position' | 'trend_alignment' | 'momentum' | 'volume';
  direction: 'bullish' | 'bearish' | 'neutral' | 'unavailable';
  numerical_observation?: number | null;
  display_value: string;
  rule_threshold: string;
  explanation: string;
  evidence_ref: string;
  is_valid: boolean;
}

export interface TechnicalPriceSummary {
  latest_date: string;
  latest_close: number;
  previous_close?: number | null;
  latest_open: number;
  latest_high: number;
  latest_low: number;
  latest_volume: number;
  average_volume_20?: number | null;
  relative_volume?: number | null;
  latest_daily_return_pct?: number | null;
  period_high: number;
  period_low: number;
  distance_from_period_high_pct?: number | null;
  distance_from_period_low_pct?: number | null;
}

export interface TechnicalIndicatorSummary {
  sma_20?: number | null;
  sma_50?: number | null;
  close_vs_sma_20_pct?: number | null;
  close_vs_sma_50_pct?: number | null;
  sma_20_slope_5d?: number | null;
  sma_50_slope_5d?: number | null;
  rsi_14?: number | null;
  volatility_20_annualized_pct?: number | null;
  trend_20_vs_50?: string | null;
}

export interface TechnicalAnalysisResponse {
  ticker: string;
  resolved_ticker: string;
  company_name?: string | null;
  analysis_timestamp: string;
  data_as_of: string;
  provider: string;
  model: string;
  deterministic_classification: 'Bullish' | 'Bearish' | 'Mixed / Neutral' | 'Insufficient Data';
  classification_score?: number | null;
  classification_rationale: string;
  deterministic_signals: DeterministicSignal[];
  short_term_price_action: string;
  medium_term_trend: string;
  price_summary: TechnicalPriceSummary;
  indicator_summary: TechnicalIndicatorSummary;
  bullish_signals: string[];
  bearish_signals: string[];
  trend_interpretation: string;
  risk_factors: string[];
  missing_data: string[];
  uncertainties: string[];
  evidence: string[];
  conclusion: string;
  disclaimer: string;
}

export interface ProviderStatusResponse {
  status: 'ok' | 'degraded' | 'unreachable' | 'error' | 'configured' | 'unconfigured';
  provider: string;
  configured_model: string;
  base_url?: string;
  model_installed?: boolean;
  available_models?: string[];
  message?: string;
}
