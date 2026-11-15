export interface EvalRun {
  id: string;
  run_name: string;
  pipeline_version?: string | null;
  faithfulness?: number | null;
  answer_relevancy?: number | null;
  context_precision?: number | null;
  context_recall?: number | null;
  recall_at_10?: number | null;
  extra_metrics?: Record<string, unknown> | null;
  created_at: string;
}

export function getBenchmark(run: EvalRun): string {
  return (run.extra_metrics?.benchmark as string) ?? "golden";
}

export function getPrimaryScore(run: EvalRun): number | null {
  const bm = getBenchmark(run);
  if (bm === "legalbench_rag") return run.recall_at_10 ?? (run.extra_metrics?.recall_at_10 as number) ?? null;
  if (bm === "cuad") return (run.extra_metrics?.token_f1 as number) ?? run.recall_at_10 ?? null;
  if (bm === "contract_nli") return (run.extra_metrics?.accuracy as number) ?? null;
  if (run.faithfulness != null) return run.faithfulness;
  return null;
}

export function getPrimaryLabel(run: EvalRun): string {
  const bm = getBenchmark(run);
  if (bm === "legalbench_rag") return "Recall@10";
  if (bm === "cuad") return "Token F1";
  if (bm === "contract_nli") return "Accuracy";
  return "Faithfulness";
}

export interface GoldenCase {
  question: string;
  ground_truth: string;
  category: string;
}
