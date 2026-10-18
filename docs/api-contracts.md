# TradeRunner — Multi-Agent Stock Analysis Platform — API Contracts

This document formalizes the HTTP REST interface, schema conventions, and error formats for the platform.

## Base URL
- Development: `http://localhost:8000`
- API Version Prefix: `/api/v1`

---

## 1. Standard Error Envelope

All API errors return a uniform JSON envelope with a predictable structure:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR | NOT_FOUND | DATABASE_UNAVAILABLE | INTERNAL_SERVER_ERROR",
    "message": "Human-readable description of what failed",
    "details": null
  }
}
```

### Standard Error Status Codes
- `400 Bad Request`: Invalid business logic parameters.
- `401 Unauthorized`: Missing or invalid authentication token.
- `403 Forbidden`: Authenticated user lacks ownership of requested resource.
- `404 Not Found`: Target entity ID does not exist.
- `422 Unprocessable Entity`: Request body violates Pydantic schema validation.
- `500 Internal Server Error`: Unhandled exception (sanitized in production, no stack traces leaked).
- `503 Service Unavailable`: Critical dependency connection failed.

---

## 2. Health Endpoints

### 2.1 Get Health & Readiness Status
- **Method**: `GET`
- **Paths**:
  - `/api/v1/health` (Canonical)
  - `/api/health` (Convenience alias)
- **Authentication**: None required (Public)

#### Response `200 OK` (Healthy):
```json
{
  "status": "healthy",
  "timestamp": "2026-10-15T21:30:00.000Z",
  "app": {
    "status": "ok",
    "name": "Multi-Agent Stock Analysis Platform",
    "version": "0.1.0",
    "environment": "development",
    "uptime_seconds": 142.5
  },
  "dependencies": {
    "database": {
      "name": "postgresql",
      "status": "healthy",
      "latency_ms": 1.25,
      "message": "Database reachable and responsive"
    }
  }
}
```

#### Response `200 OK` (Degraded Dependency):
```json
{
  "status": "degraded",
  "timestamp": "2026-10-15T21:30:00.000Z",
  "app": {
    "status": "ok",
    "name": "Multi-Agent Stock Analysis Platform",
    "version": "0.1.0",
    "environment": "development",
    "uptime_seconds": 150.2
  },
  "dependencies": {
    "database": {
      "name": "postgresql",
      "status": "unhealthy",
      "latency_ms": 3005.12,
      "message": "Database ping failed: ConnectionRefusedError"
    }
  }
}
```

---

## 3. Stock Analysis Endpoints

### 3.1 Initiate Analysis Run
- **Method**: `POST`
- **Path**: `/api/v1/analysis`
- **Headers**: `Content-Type: application/json`

#### Request Body:
```json
{
  "ticker": "AAPL",
  "agent_types": ["fundamentals", "technical", "risk"],
  "parameters": {
    "discount_rate": 0.08,
    "growth_rate_terminal": 0.025
  }
}
```

#### Response `201 Created`:
```json
{
  "id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "ticker": "AAPL",
  "status": "pending",
  "parameters": {
    "agent_types": ["fundamentals", "technical", "risk"],
    "custom_params": {
      "discount_rate": 0.08,
      "growth_rate_terminal": 0.025
    }
  },
  "result_summary": null,
  "created_at": "2026-10-15T21:35:10.500Z",
  "updated_at": "2026-10-15T21:35:10.500Z"
}
```

### 3.2 Get Analysis Run Status
- **Method**: `GET`
- **Path**: `/api/v1/analysis/{run_id}`

#### Response `200 OK`:
```json
{
  "id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "ticker": "AAPL",
  "status": "completed",
  "parameters": { ... },
  "result_summary": "Multi-agent consensus: Strong intrinsic value with 14% margin of safety.",
  "created_at": "2026-10-15T21:35:10.500Z",
  "updated_at": "2026-10-15T21:35:45.200Z"
}
```

### 3.3 List Historical Analysis Runs
- **Method**: `GET`
- **Path**: `/api/v1/analysis?limit=10&offset=0`

#### Response `200 OK`:
```json
[
  {
    "id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
    "ticker": "AAPL",
    "status": "completed",
    "parameters": { ... },
    "result_summary": "...",
    "created_at": "2026-10-15T21:35:10.500Z",
    "updated_at": "2026-10-15T21:35:45.200Z"
  }
]
```

---

## 4. Market Data API (Milestone 1)

### 4.1 Get Daily Historical Market Data & Indicators
- **Method**: `GET`
- **Path**: `/api/v1/market-data/{ticker}?period=6mo`
- **Query Parameters**:
  - `period`: Historical lookback window (`1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`). Default: `6mo`.

#### Response `200 OK`:
```json
{
  "requested_ticker": "TCS",
  "provider_ticker": "TCS.NS",
  "provider": "Yahoo Finance (via yfinance daily historical)",
  "is_live_price": false,
  "price_series_convention": "raw_close",
  "retrieval_timestamp": "2026-10-17T15:35:00.000000Z",
  "latest_trading_date": "2026-10-16",
  "latest_close": 2465.0,
  "company": {
    "name": "Tata Consultancy Services Limited",
    "currency": "INR",
    "exchange": "NSI",
    "sector": "Information Technology",
    "industry": "Information Technology Services"
  },
  "validation": {
    "status": "valid",
    "total_records": 22,
    "issues": [
      {
        "code": "DIVIDEND_EVENT_DETECTED",
        "message": "Cash dividend event recorded on 2026-10-14. Raw Close reflects settlement price, while Adj Close incorporates dividend reinvestment adjustment.",
        "severity": "info",
        "details": { "dividend_dates": ["2026-10-14"] }
      },
      {
        "code": "LIMITED_HISTORY_WARNING",
        "message": "Dataset contains 22 sessions (< 50). 50-SMA will be unavailable.",
        "severity": "info",
        "details": { "record_count": 22 }
      }
    ],
    "warnings_count": 0,
    "errors_count": 0
  },
  "indicators_summary": {
    "latest_daily_return_pct": 4.8936,
    "latest_sma_20": 2143.35,
    "latest_sma_50": null,
    "latest_volatility_20_annualized_pct": 39.0,
    "trend_20_vs_50": "insufficient_data"
  },
  "price_history": [
    {
      "date": "2026-10-16",
      "open": 2382.0,
      "high": 2484.7,
      "low": 2375.7,
      "close": 2465.0,
      "adj_close": 2465.0,
      "volume": 12166634
    }
  ],
  "indicator_series": [
    {
      "date": "2026-10-16",
      "daily_return_pct": 4.8936,
      "sma_20": 2143.35,
      "sma_50": null,
      "volatility_20_annualized_pct": 39.0
    }
  ]
}
```

### 4.2 Calculation & Corporate Action Conventions
- **Dates**: Preserves local exchange trading calendar dates (`YYYY-MM-DD`). Does not apply UTC timezone conversion to prevent shifting Friday/Monday sessions to weekends.
- **Price Series**: Open, High, Low, and Close represent raw, unadjusted exchange transaction levels. `adj_close` incorporates dividend reinvestment and split factors.
- **Indicators**:
  - `daily_return_pct`: `((Close_t / Close_{t-1}) - 1) * 100` on raw Close.
  - `sma_20` / `sma_50`: Rolling arithmetic mean of raw Close over 20 and 50 sessions; requires 20 and 50 sessions respectively.
  - `volatility_20_annualized_pct`: Sample standard deviation (`ddof=1`) of 20 daily percentage return values scaled by `sqrt(252)` trading days per year. Requires 20 daily returns (21 price sessions). Returns `null` if fewer sessions are available.

### 4.3 Technical Stock Analysis (Milestone 2)
- **Method**: `POST`
- **Path**: `/api/v1/analysis/technical`
- **Headers**: `Content-Type: application/json`

#### Request Body:
```json
{
  "ticker": "TCS",
  "period": "6mo"
}
```

#### Response `200 OK`:
```json
{
  "ticker": "TCS.NS",
  "company_name": "Tata Consultancy Services Limited",
  "currency": "INR",
  "analysis_timestamp": "2026-10-18T11:20:00Z",
  "data_as_of": "2026-10-16",
  "provider": "ollama",
  "model": "deepseek-r1:7b",
  "price_summary": {
    "latest_close": 3520.50,
    "period_open": 3410.00,
    "period_high": 3615.00,
    "period_low": 3280.00,
    "period_return_pct": 3.24,
    "latest_volume": 2105400
  },
  "indicator_summary": {
    "latest_sma_20": 3495.20,
    "latest_sma_50": 3440.10,
    "latest_volatility_20_annualized_pct": 18.45,
    "trend_20_vs_50": "bullish"
  },
  "bullish_signals": [
    "Price is trading above both 20-session SMA (3495.20) and 50-session SMA (3440.10).",
    "Positive 20-session vs 50-session alignment (golden cross configuration)."
  ],
  "bearish_signals": [
    "Volume contraction during recent advance indicates waning participation."
  ],
  "trend_interpretation": "TCS exhibits a moderate upward trend supported by moving average alignment.",
  "risk_factors": [
    "Annualized 20-session volatility at 18.45% indicates potential medium-term swings."
  ],
  "missing_data": [],
  "uncertainties": [
    "Past technical structure does not predict corporate earnings surprises."
  ],
  "evidence": [
    "Latest close 3520.50 > SMA 20 (3495.20) > SMA 50 (3440.10)."
  ],
  "conclusion": "Informational technical summary: Market structure remains constructive above 50-SMA. This analysis is historical and does not constitute financial advice or an automated trading recommendation."
}
```

### 4.4 LLM Provider Diagnostic Status (Milestone 2)
- **Method**: `GET`
- **Path**: `/api/v1/analysis/provider-status`

#### Response `200 OK`:
```json
{
  "status": "ok",
  "provider": "ollama",
  "base_url": "http://localhost:11434",
  "configured_model": "deepseek-r1:7b",
  "model_installed": true,
  "available_models": ["deepseek-r1:7b", "deepseek-r1:14b", "qwen3:8b"]
}
```


---

## 5. Future Endpoints Roadmap

| Method | Endpoint | Description | Phase |
|---|---|---|---|
| `GET` | `/api/v1/analysis/{run_id}/stream` | Server-Sent Events (SSE) streaming live agent thought chains | Phase 2 |
| `GET` | `/api/v1/watchlists` | User stock watchlists (Supabase Auth protected) | Phase 2 |
| `POST` | `/api/v1/reports/{run_id}/export` | Generate PDF / Markdown audit report with primary source citations | Phase 3 |

