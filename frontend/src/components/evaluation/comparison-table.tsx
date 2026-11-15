"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { BarChart3 } from "lucide-react";
import { type EvalRun, getBenchmark, getPrimaryScore, getPrimaryLabel } from "@/types/evaluation";

const columnHelper = createColumnHelper<EvalRun>();

function ScoreCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-muted-foreground">--</span>;
  const color = value >= 0.8 ? "text-success" : value >= 0.5 ? "text-warning" : "text-danger";
  return <span className={`font-medium ${color}`}>{value.toFixed(3)}</span>;
}

const BENCHMARK_LABELS: Record<string, string> = {
  golden: "Golden QA",
  cuad: "CUAD",
  legalbench_rag: "LegalBench",
  contract_nli: "ContractNLI",
};

const columns = [
  columnHelper.accessor("run_name", {
    header: "Run",
    cell: (i) => {
      const bm = getBenchmark(i.row.original);
      return (
        <div>
          <span className="font-medium text-foreground">{BENCHMARK_LABELS[bm] ?? bm}</span>
          <span className="block text-[10px] text-muted-foreground">{i.getValue()}</span>
        </div>
      );
    },
  }),
  columnHelper.display({
    id: "score",
    header: "Score",
    cell: (i) => {
      const run = i.row.original;
      const score = getPrimaryScore(run);
      const label = getPrimaryLabel(run);
      return (
        <div>
          <ScoreCell value={score} />
          <span className="text-[10px] text-muted-foreground">{label}</span>
        </div>
      );
    },
  }),
  columnHelper.accessor("faithfulness", {
    header: "Faith.",
    cell: (i) => <ScoreCell value={i.getValue()} />,
  }),
  columnHelper.accessor("recall_at_10", {
    header: "Recall@10",
    cell: (i) => {
      const run = i.row.original;
      const val = run.recall_at_10 ?? (run.extra_metrics?.recall_at_10 as number) ?? (run.extra_metrics?.retrieval_recall_at_10 as number) ?? null;
      return <ScoreCell value={val} />;
    },
  }),
  columnHelper.display({
    id: "groundedness",
    header: "Ground.",
    cell: (i) => {
      const v = i.row.original.extra_metrics?.groundedness as number | undefined;
      return <ScoreCell value={v ?? null} />;
    },
  }),
  columnHelper.display({
    id: "hallucination",
    header: "Halluc.",
    cell: (i) => {
      const v = i.row.original.extra_metrics?.hallucination_rate as number | undefined;
      if (v == null) return <span className="text-muted-foreground">--</span>;
      const color = v <= 0.1 ? "text-success" : v <= 0.3 ? "text-warning" : "text-danger";
      return <span className={`font-medium ${color}`}>{v.toFixed(3)}</span>;
    },
  }),
  columnHelper.display({
    id: "citation_coverage",
    header: "Cit.Cov",
    cell: (i) => {
      const v = i.row.original.extra_metrics?.citation_coverage as number | undefined;
      return <ScoreCell value={v ?? null} />;
    },
  }),
  columnHelper.display({
    id: "samples",
    header: "Samples",
    cell: (i) => {
      const n = i.row.original.extra_metrics?.samples as number | undefined;
      return <span className="text-xs text-muted-foreground">{n ?? "--"}</span>;
    },
  }),
];

export function ComparisonTable({ runs }: { runs?: EvalRun[] }) {
  const table = useReactTable({
    data: runs ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!runs?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted">
          <BarChart3 className="h-5 w-5 text-muted-foreground" />
        </div>
        <p className="mt-3 text-sm font-medium text-foreground">No evaluation runs yet</p>
        <p className="mt-1 max-w-[200px] text-xs text-muted-foreground">
          POST to /api/v1/evaluation/run to create your first evaluation run.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border">
              {hg.headers.map((h) => (
                <th key={h.id} className="px-3 py-2.5 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b border-border/50 transition-colors hover:bg-secondary/30">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2.5 text-xs">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
