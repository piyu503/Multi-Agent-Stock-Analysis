export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unreachable';

export interface DependencyHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number | null;
  message?: string | null;
}

export interface AppHealth {
  status: string;
  name: string;
  version: string;
  environment: string;
  uptime_seconds: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  app: AppHealth;
  dependencies: Record<string, DependencyHealth>;
}

export interface HealthState {
  data: HealthResponse | null;
  status: HealthStatus;
  latencyMs: number | null;
  lastChecked: Date | null;
  isLoading: boolean;
  errorMessage: string | null;
}
