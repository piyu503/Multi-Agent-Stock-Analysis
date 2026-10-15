'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { fetchBackendHealth } from '@/lib/api-client';
import { env } from '@/lib/env';
import { HealthState } from '@/types/health';
import { Badge, BadgeVariant } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

export const HealthStatusIndicator: React.FC = () => {
  const [state, setState] = useState<HealthState>({
    data: null,
    status: 'unreachable',
    latencyMs: null,
    lastChecked: null,
    isLoading: true,
    errorMessage: null,
  });

  const runHealthCheck = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, errorMessage: null }));

    try {
      const { data, latencyMs } = await fetchBackendHealth();
      setState({
        data,
        status: data.status,
        latencyMs,
        lastChecked: new Date(),
        isLoading: false,
        errorMessage: null,
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Backend unreachable';
      setState({
        data: null,
        status: 'unreachable',
        latencyMs: null,
        lastChecked: new Date(),
        isLoading: false,
        errorMessage: message,
      });
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;

    const performInitialCheck = async () => {
      try {
        const { data, latencyMs } = await fetchBackendHealth();
        if (!isCancelled) {
          setState({
            data,
            status: data.status,
            latencyMs,
            lastChecked: new Date(),
            isLoading: false,
            errorMessage: null,
          });
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          const message = err instanceof Error ? err.message : 'Backend unreachable';
          setState({
            data: null,
            status: 'unreachable',
            latencyMs: null,
            lastChecked: new Date(),
            isLoading: false,
            errorMessage: message,
          });
        }
      }
    };

    performInitialCheck();
    const interval = setInterval(performInitialCheck, 30000);

    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, []);

  const getStatusBadge = (): { label: string; variant: BadgeVariant; pulse: boolean } => {
    if (state.isLoading && !state.lastChecked) {
      return { label: 'Connecting...', variant: 'neutral', pulse: true };
    }
    switch (state.status) {
      case 'healthy':
        return { label: 'System Operational', variant: 'success', pulse: true };
      case 'degraded':
        return { label: 'Degraded (Dependency Warning)', variant: 'warning', pulse: false };
      case 'unhealthy':
        return { label: 'System Unhealthy', variant: 'error', pulse: false };
      case 'unreachable':
      default:
        return { label: 'Backend Offline', variant: 'error', pulse: false };
    }
  };

  const badgeInfo = getStatusBadge();
  const dbHealth = state.data?.dependencies?.database;

  return (
    <Card
      title="System Architecture Health"
      subtitle={`Target: ${env.apiBaseUrl}${env.apiPrefix}/health`}
      action={
        <div className="flex items-center gap-3">
          <Badge variant={badgeInfo.variant} pulse={badgeInfo.pulse}>
            {badgeInfo.label}
          </Badge>
          <button
            onClick={runHealthCheck}
            disabled={state.isLoading}
            className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 active:bg-slate-900 border border-slate-700 rounded-md transition-all disabled:opacity-50 cursor-pointer"
            title="Refresh Health"
          >
            <svg
              className={`w-3.5 h-3.5 ${state.isLoading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </button>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Metric: Gateway Health */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-xs font-medium text-slate-400">FastAPI Gateway</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className={`text-lg font-bold ${
                state.status !== 'unreachable' ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {state.status !== 'unreachable' ? 'Reachable' : 'Disconnected'}
            </span>
            {state.latencyMs !== null && (
              <span className="text-xs font-mono text-slate-400">
                {state.latencyMs}ms roundtrip
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {state.data?.app
              ? `v${state.data.app.version} (${state.data.app.environment})`
              : 'Waiting for response from port 8000'}
          </p>
        </div>

        {/* Metric: PostgreSQL Health */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-xs font-medium text-slate-400">PostgreSQL Database</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span
              className={`text-lg font-bold ${
                dbHealth?.status === 'healthy'
                  ? 'text-emerald-400'
                  : state.status === 'unreachable'
                  ? 'text-slate-500'
                  : 'text-amber-400'
              }`}
            >
              {state.status === 'unreachable'
                ? 'Unknown'
                : dbHealth?.status === 'healthy'
                ? 'Connected'
                : 'Degraded / Pending'}
            </span>
            {dbHealth?.latency_ms !== null && dbHealth?.latency_ms !== undefined && (
              <span className="text-xs font-mono text-slate-400">
                {dbHealth.latency_ms}ms ping
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {state.status === 'unreachable'
              ? 'Dependency check paused'
              : dbHealth?.message || 'Async connection pool active'}
          </p>
        </div>

        {/* Metric: Engine Uptime */}
        <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-xs font-medium text-slate-400">Backend Uptime</div>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-lg font-bold text-slate-200">
              {state.data?.app
                ? `${state.data.app.uptime_seconds.toFixed(0)}s`
                : '--'}
            </span>
            <span className="text-xs text-slate-500">process lifetime</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {state.lastChecked
              ? `Checked at ${state.lastChecked.toLocaleTimeString()}`
              : 'Never checked'}
          </p>
        </div>
      </div>

      {/* Offline Diagnostic Alert */}
      {state.status === 'unreachable' && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-800/50 text-xs text-rose-300">
          <div className="font-semibold flex items-center gap-1.5 mb-1 text-rose-200">
            <svg className="w-4 h-4 text-rose-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Backend Server Not Reachable
          </div>
          <p className="text-slate-300">
            {state.errorMessage}
          </p>
          <div className="mt-2 text-slate-400 font-mono text-[11px] bg-slate-950/70 p-2 rounded border border-slate-800">
            Start backend with: <span className="text-emerald-400">cd backend; .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000</span>
          </div>
        </div>
      )}

      {/* Degraded Diagnostic (e.g. DB container not running) */}
      {state.status === 'degraded' && (
        <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300">
          <div className="font-semibold flex items-center gap-1.5 mb-1 text-amber-200">
            <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            Application Running in Degraded Mode
          </div>
          <p className="text-slate-300">
            The FastAPI server is healthy and responding, but PostgreSQL connectivity is pending or unavailable.
          </p>
          <div className="mt-2 text-slate-400 font-mono text-[11px] bg-slate-950/70 p-2 rounded border border-slate-800">
            Start PostgreSQL via Docker: <span className="text-emerald-400">docker compose up -d</span>
          </div>
        </div>
      )}
    </Card>
  );
};
