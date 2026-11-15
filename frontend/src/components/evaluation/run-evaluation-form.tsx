"use client";

import { useState } from "react";
import { Play, Loader2, CheckCircle2, FlaskConical } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

const BENCHMARKS = [
  {
    id: "golden",
    label: "Golden QA",
    description: "Legal document QA — tests answer quality against real or synthetic datasets",
    icon: "📝",
  },
  {
    id: "cuad",
    label: "CUAD",
    description: "Contract clause extraction — tests if the system can find specific clauses",
    icon: "📄",
  },
  {
    id: "legalbench_rag",
    label: "LegalBench RAG",
    description: "Legal retrieval benchmark — tests if the search engine finds the right passages",
    icon: "🔍",
  },
  {
    id: "contract_nli",
    label: "ContractNLI",
    description: "NDA entailment — tests if the AI can reason about contract statements",
    icon: "⚖️",
  },
] as const;

const DATASET_OPTIONS = [
  { id: "legal", label: "Real Documents", description: "10 verified QA pairs against your uploaded SEC EDGAR contracts" },
  { id: "synthetic", label: "Synthetic", description: "213 generic legal QA pairs (fictional companies)" },
  { id: "both", label: "Both", description: "Run legal and synthetic separately, compare results" },
] as const;

export function RunEvaluationForm({ onStarted }: { onStarted?: () => void }) {
  const [selected, setSelected] = useState<string>("golden");
  const [dataset, setDataset] = useState<string>("legal");
  const [smokeOnly, setSmokeOnly] = useState(true);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);

  const isGolden = selected === "golden";

  const handleRun = async () => {
    setRunning(true);
    setDone(false);
    try {
      await apiFetch("/api/v1/evaluation/run", {
        method: "POST",
        body: JSON.stringify({
          run_name: `${selected}-${Date.now()}`,
          benchmark: selected,
          dataset: isGolden ? dataset : "legal",
          smoke_only: smokeOnly,
          max_pairs: smokeOnly ? 5 : (dataset === "legal" ? 10 : 50),
        }),
      });
      setDone(true);
      onStarted?.();
    } catch (err) {
      console.error("Failed to start evaluation:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card className="animate-fade-in border-dashed">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <FlaskConical className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Run an Evaluation
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Pick a benchmark, hit run, and the system will grade itself.
              Results appear below once finished.
            </p>
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {BENCHMARKS.map((b) => (
            <button
              key={b.id}
              type="button"
              onClick={() => {
                setSelected(b.id);
                setDone(false);
              }}
              className={`rounded-lg border p-3 text-left transition-all ${
                selected === b.id
                  ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                  : "border-border bg-card hover:bg-secondary/40"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-base">{b.icon}</span>
                <span className="text-xs font-semibold text-foreground">
                  {b.label}
                </span>
              </div>
              <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                {b.description}
              </p>
            </button>
          ))}
        </div>

        {isGolden && (
          <div className="mt-3">
            <p className="text-[11px] font-medium text-muted-foreground mb-1.5">Dataset</p>
            <div className="flex gap-2">
              {DATASET_OPTIONS.map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => { setDataset(d.id); setDone(false); }}
                  className={`flex-1 rounded-md border px-2.5 py-1.5 text-left transition-all ${
                    dataset === d.id
                      ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                      : "border-border hover:bg-secondary/40"
                  }`}
                >
                  <span className="text-[11px] font-semibold text-foreground">{d.label}</span>
                  <p className="text-[10px] text-muted-foreground leading-tight">{d.description}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={smokeOnly}
              onChange={(e) => setSmokeOnly(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-border accent-primary"
            />
            Quick mode (fewer questions, faster results)
          </label>

          <Button
            size="sm"
            onClick={handleRun}
            disabled={running}
            className="gap-1.5"
          >
            {running ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Running...
              </>
            ) : done ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" />
                Started! Refresh in ~15 min
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5" />
                Run Evaluation
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
