"use client";

import { Header } from "@/components/layout/header";
import { EvalRadarChart } from "@/components/evaluation/radar-chart";
import { ComparisonTable } from "@/components/evaluation/comparison-table";
import { MetricsCards } from "@/components/evaluation/metrics-cards";
import { RunEvaluationForm } from "@/components/evaluation/run-evaluation-form";
import { useEvaluationResults, useLatencyStats, useCostStats } from "@/hooks/use-evaluation";
import { AlertCircle, BarChart3, RefreshCw, Timer, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";

function fmtMs(seconds: number | null | undefined): string {
  if (seconds == null) return "--";
  return seconds < 1 ? `${Math.round(seconds * 1000)}ms` : `${seconds.toFixed(2)}s`;
}

function PerformancePanel() {
  const { data: latency } = useLatencyStats();
  const { data: cost } = useCostStats();

  const stages = latency
    ? [
        { name: "Retrieval", ...latency.retrieval },
        { name: "Rerank", ...latency.rerank },
        { name: "Generation", ...latency.generation },
        { name: "End-to-End", ...latency.e2e },
      ]
    : [];

  return (
    <div className="grid gap-6 lg:grid-cols-2 animate-fade-in">
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Timer className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Latency (P50 / P95 / P99)</h3>
        </div>
        {stages.length > 0 ? (
          <div className="space-y-3">
            {stages.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <span className="font-medium text-foreground">{s.name}</span>
                <span className="text-muted-foreground">
                  {fmtMs(s.p50)} / <span className="font-semibold text-foreground">{fmtMs(s.p95)}</span> / {fmtMs(s.p99)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No latency data yet. Send some queries first.</p>
        )}
      </div>
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Cost Tracking</h3>
        </div>
        {cost ? (
          <div className="space-y-3 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total queries</span>
              <span className="font-semibold text-foreground">{cost.total_queries}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Avg cost / query</span>
              <span className="font-semibold text-foreground">${cost.avg_cost_per_query.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total spend</span>
              <span className="font-semibold text-foreground">${cost.total_cost.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Cache savings</span>
              <span className="font-semibold text-success">${cost.total_savings_from_cache.toFixed(4)} ({cost.savings_percentage.toFixed(1)}%)</span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No cost data yet. Send some queries first.</p>
        )}
      </div>
    </div>
  );
}

export default function EvaluationPage() {
  const { data, isLoading, error, refetch } = useEvaluationResults();
  const hasResults = (data?.length ?? 0) > 0;

  return (
    <>
      <Header title="Model Evaluation" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-8">
          <div className="flex items-start justify-between animate-fade-in">
            <div>
              <h2 className="text-xl font-semibold text-foreground">Evaluation Dashboard</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Grade the AI system on legal benchmarks. Run an evaluation, then check the scores below.
              </p>
            </div>
            {hasResults && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => refetch()}
                className="gap-1.5 shrink-0"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Refresh
              </Button>
            )}
          </div>

          <RunEvaluationForm onStarted={() => setTimeout(() => refetch(), 3000)} />

          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
              <AlertCircle className="h-4 w-4 text-danger shrink-0" />
              <p className="text-sm text-danger">Could not load evaluation data from the API.</p>
            </div>
          )}

          {!isLoading && !error && hasResults && (
            <>
              <MetricsCards latest={data?.[0]} runs={data} />
              <PerformancePanel />
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                  <div className="mb-4 flex items-center gap-2">
                    <BarChart3 className="h-4 w-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                      Performance Radar
                    </h3>
                  </div>
                  <EvalRadarChart runs={data} />
                </div>
                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                  <h3 className="mb-4 text-sm font-semibold text-foreground">
                    Run History
                  </h3>
                  <ComparisonTable runs={data} />
                </div>
              </div>
            </>
          )}

          {!isLoading && !error && !hasResults && (
            <div className="flex flex-col items-center justify-center py-12 text-center animate-fade-in">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
                <BarChart3 className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm font-medium text-foreground">No results yet</p>
              <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                Run your first evaluation above. It takes about a minute for the &quot;Quick mode&quot;
                golden benchmark. Hit Refresh when it&apos;s done.
              </p>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
