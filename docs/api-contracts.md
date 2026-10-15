# Multi-Agent Stock Analysis Platform — API Contracts

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

## 4. Future Endpoints Roadmap

| Method | Endpoint | Description | Phase |
|---|---|---|---|
| `GET` | `/api/v1/analysis/{run_id}/stream` | Server-Sent Events (SSE) streaming live agent thought chains | Phase 2 |
| `GET` | `/api/v1/watchlists` | User stock watchlists (Supabase Auth protected) | Phase 2 |
| `POST` | `/api/v1/reports/{run_id}/export` | Generate PDF / Markdown audit report with primary source citations | Phase 3 |
