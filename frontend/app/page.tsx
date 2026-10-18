import React from 'react';
import { HealthStatusIndicator } from '@/features/health/HealthStatusIndicator';
import { StockMarketLookup } from '@/features/market-data/StockMarketLookup';
import { TechnicalAnalysisCard } from '@/features/analysis/TechnicalAnalysisCard';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export default function Home() {
  const plannedAgents = [
    {
      name: 'Fundamentals Agent',
      role: 'Valuation & Accounting',
      desc: 'Computes DCF models, WACC, multiple comparisons (P/E, EV/EBITDA), and balance sheet solvency.',
      badge: 'Quantitative',
    },
    {
      name: 'Technical Analysis Agent',
      role: 'Market Structure & Momentum',
      desc: 'Tracks moving averages, RSI divergence, Fibonacci support/resistance, and volume profiles.',
      badge: 'Price Action',
    },
    {
      name: 'SEC & News Agent',
      role: 'Filings & Macro Catalysts',
      desc: 'Parses 10-K, 10-Q, and 8-K filings via SEC EDGAR XBRL with real-time headline credibility filtering.',
      badge: 'NLP & Search',
    },
    {
      name: 'Bull Thesis Agent',
      role: 'Growth & Competitive Moats',
      desc: 'Synthesizes market expansion, pricing power, unit economics, and favorable scenario models.',
      badge: 'Advocate',
    },
    {
      name: 'Bear Red-Team Agent',
      role: 'Forensic Audit & Downside',
      desc: 'Challenges bullish assumptions, stress-tests debt covenants, and highlights competitive vulnerabilities.',
      badge: 'Adversary',
    },
    {
      name: 'Risk Officer Agent',
      role: 'Synthesis & Evidence Citation',
      desc: 'Arbitrates bull/bear conflicts, enforces evidence citation requirements, and generates the final research memo.',
      badge: 'Governor',
    },
  ];

  const architecturalLayers = [
    {
      name: 'Presentation Layer',
      tech: 'Next.js 16 / TypeScript / Tailwind CSS',
      desc: 'Modular component architecture, live streaming progress hooks, and reactive financial dashboards.',
    },
    {
      name: 'API Gateway & Services',
      tech: 'Python FastAPI / Pydantic v2',
      desc: 'Validated REST contracts, CORS origin restriction, dependency-aware health checks, and domain services.',
    },
    {
      name: 'Agent Orchestration Engine',
      tech: 'LangGraph / Model Provider Abstraction',
      desc: 'Stateful agent cycles, parallel analyst execution, adversarial thesis debate, and Gemini/LLM interoperability.',
    },
    {
      name: 'Data Access & Migrations',
      tech: 'PostgreSQL / SQLAlchemy 2.x / Alembic',
      desc: 'Async connection pooling, transactional unit of work, UUID primary keys, and versioned DDL migrations.',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 radial-glow flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-emerald-400 flex items-center justify-center font-black text-slate-950 text-sm shadow-md shadow-indigo-500/20">
              TR
            </div>
            <div>
              <span className="font-bold tracking-tight text-white">TradeRunner</span>
              <span className="text-xs text-slate-400 ml-2 font-mono">v0.1.0-alpha</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden sm:inline-flex text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-md">
              Phase 1: Architecture Scaffold
            </span>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
            >
              API Swagger
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-10">
        {/* Hero Section */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2">
            <Badge variant="info">Multi-Agent System Architecture</Badge>
            <span className="text-xs text-slate-500">Autonomous Financial Intelligence</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            TradeRunner &bull; AI-Powered Multi-Agent Stock Analysis
          </h1>
          <p className="text-sm sm:text-base text-slate-400 max-w-3xl leading-relaxed">
            Foundational architecture designed for high-conviction equity research. Scaffolds a modular monorepo
            coordinating specialized financial agents, deterministic Python valuation tools, and stateful LangGraph workflows.
          </p>
        </div>

        {/* Live Backend Connection & Health Status Indicator */}
        <section aria-labelledby="system-health-title">
          <h2 id="system-health-title" className="sr-only">System Health</h2>
          <HealthStatusIndicator />
        </section>

        {/* Milestone 1: NSE Market Data Pipeline */}
        <section aria-labelledby="market-data-title">
          <h2 id="market-data-title" className="sr-only">Market Data Feed</h2>
          <StockMarketLookup />
        </section>

        {/* Milestone 2: Technical Stock Analyst (Local LLM) */}
        <section aria-labelledby="technical-analysis-title">
          <h2 id="technical-analysis-title" className="sr-only">Technical Stock Analysis</h2>
          <TechnicalAnalysisCard />
        </section>

        {/* Planned Agent Swarm Preview */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Planned AI Agent Swarm</h2>
              <p className="text-xs text-slate-400">Specialized agents orchestrated through LangGraph stateful workflows</p>
            </div>
            <span className="text-xs text-slate-500 font-mono">6 Specialized Roles</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plannedAgents.map((agent) => (
              <Card key={agent.name} className="hover:border-indigo-500/40">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-slate-100 text-sm">{agent.name}</h3>
                  <span className="text-[10px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60">
                    {agent.badge}
                  </span>
                </div>
                <div className="text-xs font-medium text-indigo-400 mb-1">{agent.role}</div>
                <p className="text-xs text-slate-400 leading-relaxed">{agent.desc}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Architectural Layers Breakdown */}
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white">Monorepo Layer Separation</h2>
            <p className="text-xs text-slate-400">Isolated concerns ensuring maintainability, auditability, and zero vendor lock-in</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {architecturalLayers.map((layer) => (
              <div
                key={layer.name}
                className="p-5 rounded-xl border border-slate-800/80 bg-slate-900/50 backdrop-blur-sm space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-slate-200 text-sm">{layer.name}</div>
                  <span className="text-xs font-mono text-emerald-400">{layer.tech}</span>
                </div>
                <p className="text-xs text-slate-400">{layer.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Next Steps & Verification Commands */}
        <Card title="Quick Start & Developer Verification" subtitle="Commands to verify and run the initial scaffold locally">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs">
            <div>
              <div className="font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-indigo-500" />
                Backend FastAPI Server (Port 8000)
              </div>
              <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-300 overflow-x-auto">
{`# 1. Activate venv & run server
cd backend
.\\.venv\\Scripts\\activate
uvicorn app.main:app --reload --port 8000

# 2. Run automated test suite
pytest -v`}
              </pre>
            </div>

            <div>
              <div className="font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Frontend Next.js App (Port 3000)
              </div>
              <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-slate-300 overflow-x-auto">
{`# 1. Install & run development server
cd frontend
npm run dev

# 2. Run build verification
npm run build`}
              </pre>
            </div>
          </div>
        </Card>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 mt-12 bg-slate-950/80 text-xs text-slate-500 text-center">
        <div className="max-w-7xl mx-auto px-4">
          TradeRunner Architecture &bull; Designed for LangGraph, Gemini, and PostgreSQL
        </div>
      </footer>
    </div>
  );
}
