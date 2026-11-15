"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { EvalRun } from "@/types/evaluation";

export function useEvaluationResults() {
  return useQuery({
    queryKey: ["evaluation", "results"],
    queryFn: () => apiFetch<EvalRun[]>("/api/v1/evaluation/results"),
  });
}

export interface LatencyStats {
  retrieval: { p50: number | null; p95: number | null; p99: number | null };
  rerank: { p50: number | null; p95: number | null; p99: number | null };
  generation: { p50: number | null; p95: number | null; p99: number | null };
  e2e: { p50: number | null; p95: number | null; p99: number | null };
}

export interface CostStats {
  avg_cost_per_query: number;
  total_cost: number;
  total_savings_from_cache: number;
  savings_percentage: number;
  total_queries: number;
}

export function useLatencyStats() {
  return useQuery({
    queryKey: ["metrics", "latency"],
    queryFn: () => apiFetch<LatencyStats>("/metrics/latency"),
    refetchInterval: 15000,
  });
}

export function useCostStats() {
  return useQuery({
    queryKey: ["metrics", "cost"],
    queryFn: () => apiFetch<CostStats>("/metrics/cost"),
    refetchInterval: 15000,
  });
}
