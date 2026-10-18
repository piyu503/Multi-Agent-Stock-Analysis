# TradeRunner - Multi-Agent Stock Analysis Platform

An institutional-grade, AI-powered stock analysis platform designed to orchestrate specialized AI agents for deep equity research, financial statement parsing, DCF valuation modeling, and dialectic Bull/Bear thesis stress-testing.

---

## 1. System Architecture

The project is structured as a modular monorepo:

```
stock-analysis-platform/
├── frontend/             # Next.js 16 + React 19 + TypeScript + Tailwind CSS
├── backend/              # Python 3.12 + FastAPI + SQLAlchemy 2.x + Alembic
├── docs/                 # Architecture specifications and API contracts
│   ├── architecture.md   # Architectural breakdown and design rationale
│   └── api-contracts.md  # Formal API request/response contracts
├── docker-compose.yml    # Local PostgreSQL 16 container definition
├── .env.example          # Environment variable template
└── README.md             # Developer setup and operations guide
```

Detailed architectural diagrams and layer responsibilities are documented in [`docs/architecture.md`](docs/architecture.md).

---

## 2. Prerequisites

Ensure you have the following installed locally:
- **Node.js**: v20+ or v24+ (`node --version`)
- **Python**: 3.11+ or 3.12+ (`python --version` or `py -3.12 --version`)
- **Docker**: (Optional, for running local PostgreSQL container)

---

## 3. Environment Configuration

1. Copy the example configuration to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```

2. (Optional) For the frontend, create `frontend/.env.local` if you need custom API URLs:
   ```bash
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
   ```

---

## 4. Quick Start (Development)

### A. Start the PostgreSQL Database (Optional / Recommended)

If you have Docker Desktop running:
```bash
docker compose up -d
```
> **Note**: If PostgreSQL is not running, the FastAPI backend will still start and operate in **degraded mode** (reporting that the database dependency is unreachable while keeping the API gateway alive).

### B. Setup and Run the Backend (FastAPI)

1. Navigate to `backend`:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```powershell
   # Windows (PowerShell)
   py -3.12 -m venv .venv
   .\.venv\Scripts\activate

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Run database migrations:
   ```bash
   # Offline SQL preview
   alembic upgrade head --sql

   # Execute migrations against target database
   alembic upgrade head
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Canonical Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
   - Convenience Health Alias: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### C. Setup and Run the Frontend (Next.js)

1. Open a new terminal and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   - Web Application: [http://localhost:3000](http://localhost:3000)

---

## 5. Automated Testing & Verification

### Backend Tests (Pytest)

The backend test suite runs with an isolated, in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) so tests execute in milliseconds without requiring external PostgreSQL services:

```powershell
# In backend directory with .venv active:
pytest -v
```

### Frontend Build & Lint Checks

Verify TypeScript types, Tailwind CSS compilation, and ESLint rules:

```bash
# In frontend directory:
npm run lint
npm run build
```

---

## 6. API Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Comprehensive application and dependency health status |
| `GET` | `/api/health` | Root health convenience alias |
| `POST` | `/api/v1/analysis` | Initiate a multi-agent stock analysis run |
| `GET` | `/api/v1/analysis/{id}` | Retrieve status and findings for an analysis run |
| `GET` | `/api/v1/analysis` | List historical analysis runs |

See [`docs/api-contracts.md`](docs/api-contracts.md) for complete schema definitions.

---

## 7. Next Phase: Multi-Agent Implementation Roadmap

The scaffolded codebase is now ready for **Phase 2**:
1. **LangGraph Graph Implementation**: Connecting the supervisor node, parallel analysts, and dialectic debate in `app/graphs/`.
2. **Model Provider Gateway**: Implementing the Gemini 2.0 / 1.5 Pro client adapter in `app/core/llm.py`.
3. **Deterministic Financial Tools**: Parsing SEC 10-K filings via XBRL and calculating DCF valuations in `app/tools/`.
4. **Agent State Streaming**: Exposing Server-Sent Events (SSE) to stream live agent reasoning steps to the Next.js frontend.
