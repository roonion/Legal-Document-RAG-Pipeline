"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart as ReRadarChart,
  ResponsiveContainer,
  Legend,
} from "recharts";

import { type EvalRun, getBenchmark, getPrimaryScore } from "@/types/evaluation";

function buildRadarData(runs?: EvalRun[]) {
  if (!runs?.length) {
    return [
      { metric: "LegalBench", score: 0 },
      { metric: "Golden QA", score: 0 },
      { metric: "CUAD", score: 0 },
      { metric: "ContractNLI", score: 0 },
    ];
  }

  const bestByBenchmark: Record<string, number> = {};
  for (const r of runs) {
    const bm = getBenchmark(r);
    const score = getPrimaryScore(r);
    if (score != null && (bestByBenchmark[bm] == null || score > bestByBenchmark[bm])) {
      bestByBenchmark[bm] = score;
    }
  }

  return [
    { metric: "LegalBench", score: bestByBenchmark["legalbench_rag"] ?? 0 },
    { metric: "Golden QA", score: bestByBenchmark["golden"] ?? 0 },
    { metric: "CUAD", score: bestByBenchmark["cuad"] ?? 0 },
    { metric: "ContractNLI", score: bestByBenchmark["contract_nli"] ?? 0 },
  ];
}

export function EvalRadarChart({ runs }: { runs?: EvalRun[] }) {
  const data = buildRadarData(runs);

  return (
    <div className="h-72 min-h-[280px] w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <ReRadarChart data={data}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
          />
          <Radar
            name="Best Score"
            dataKey="score"
            stroke="var(--primary)"
            fill="var(--primary)"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "var(--muted-foreground)" }}
          />
        </ReRadarChart>
      </ResponsiveContainer>
    </div>
  );
}
