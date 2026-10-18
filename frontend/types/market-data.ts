export type ValidationSeverity = 'info' | 'warning' | 'error';
export type ValidationStatus = 'valid' | 'warning' | 'invalid';

export interface ValidationIssue {
  code: string;
  message: string;
  severity: ValidationSeverity;
  details?: Record<string, unknown> | null;
}

export interface ValidationResult {
  status: ValidationStatus;
  total_records: number;
  issues: ValidationIssue[];
  warnings_count: number;
  errors_count: number;
}

export interface DailyBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  adj_close?: number | null;
  volume: number;
}

export interface IndicatorSeries {
  date: string;
  daily_return_pct?: number | null;
  sma_20?: number | null;
  sma_50?: number | null;
  volatility_20_annualized_pct?: number | null;
}

export interface IndicatorSummary {
  latest_daily_return_pct?: number | null;
  latest_sma_20?: number | null;
  latest_sma_50?: number | null;
  latest_volatility_20_annualized_pct?: number | null;
  trend_20_vs_50?: string | null;
}

export interface CompanyInfo {
  name?: string | null;
  currency?: string | null;
  exchange?: string | null;
  sector?: string | null;
  industry?: string | null;
}

export interface MarketDataResponse {
  requested_ticker: string;
  provider_ticker: string;
  provider: string;
  is_live_price: boolean;
  price_series_convention?: string;
  retrieval_timestamp: string;
  latest_trading_date?: string | null;
  latest_close?: number | null;
  company: CompanyInfo;
  validation: ValidationResult;
  indicators_summary: IndicatorSummary;
  price_history: DailyBar[];
  indicator_series: IndicatorSeries[];
}
