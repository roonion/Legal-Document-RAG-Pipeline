import { Card, CardContent } from "@/components/ui/card";
import { Target, Eye, Crosshair, Search, ShieldCheck, Quote, DollarSign, Timer } from "lucide-react";
import type { EvalRun } from "@/types/evaluation";

function ScoreRing({ value, label, invert }: { value: number | null | undefined; label?: string; invert?: boolean }) {
  const display = value != null ? value.toFixed(2) : "--";
  const pct = value != null ? Math.round(value * 100) : 0;
  const effective = invert && value != null ? 1 - value : value;
  const color =
    effective == null ? "text-muted-foreground" : effective >= 0.8 ? "text-success" : effective >= 0.5 ? "text-warning" : "text-danger";

  return (
    <div className="flex items-baseline gap-1">
      <span className={`text-2xl font-bold ${color}`}>{display}</span>
      {value != null && (
        <span className="text-xs text-muted-foreground">({pct}%)</span>
      )}
      {label && <span className="text-[10px] text-muted-foreground ml-1">{label}</span>}
    </div>
  );
}

function bestVal(runs: EvalRun[], getter: (r: EvalRun) => number | null | undefined): { value: number | null; source?: string } {
  let best: number | null = null;
  let source: string | undefined;
  for (const r of runs) {
    const v = getter(r);
    if (v != null && (best == null || v > best)) {
      best = v;
      source = r.run_name;
    }
  }
  return { value: best, source };
}

function lowestVal(runs: EvalRun[], getter: (r: EvalRun) => number | null | undefined): { value: number | null; source?: string } {
  let best: number | null = null;
  let source: string | undefined;
  for (const r of runs) {
    const v = getter(r);
    if (v != null && (best == null || v < best)) {
      best = v;
      source = r.run_name;
    }
  }
  return { value: best, source };
}

function extraNum(r: EvalRun, key: string): number | null {
  const v = r.extra_metrics?.[key];
  return typeof v === "number" ? v : null;
}

export function MetricsCards({ latest, runs }: { latest?: EvalRun | null; runs?: EvalRun[] }) {
  const all = runs ?? (latest ? [latest] : []);

  const recall = bestVal(all, (r) => r.recall_at_10 ?? extraNum(r, "recall_at_10"));
  const faith = bestVal(all, (r) => r.faithfulness);
  const relev = bestVal(all, (r) => r.answer_relevancy);
  const prec = bestVal(all, (r) => r.context_precision);
  const groundedness = bestVal(all, (r) => extraNum(r, "groundedness"));
  const hallucination = lowestVal(all, (r) => extraNum(r, "hallucination_rate"));
  const citCoverage = bestVal(all, (r) => extraNum(r, "citation_coverage"));
  const citDensity = bestVal(all, (r) => extraNum(r, "citation_density"));

  const primaryItems = [
    { title: "Recall@10", value: recall.value, icon: Search, description: "How many relevant docs found", source: recall.source },
    { title: "Faithfulness", value: faith.value, icon: Eye, description: "Answers grounded in sources", source: faith.source },
    { title: "Answer Relevancy", value: relev.value, icon: Target, description: "How relevant the answer is", source: relev.source },
    { title: "Context Precision", value: prec.value, icon: Crosshair, description: "Quality of retrieved context", source: prec.source },
  ];

  const qualityItems = [
    { title: "Groundedness", value: groundedness.value, icon: ShieldCheck, description: "Claims supported by context", source: groundedness.source },
    { title: "Hallucination Rate", value: hallucination.value, icon: ShieldCheck, description: "Lower is better", source: hallucination.source, invert: true },
    { title: "Citation Coverage", value: citCoverage.value, icon: Quote, description: "Sources cited in answers", source: citCoverage.source },
    { title: "Citation Density", value: citDensity.value, icon: Quote, description: "Citations per 100 words", source: citDensity.source },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {primaryItems.map((k, i) => (
          <Card key={k.title} className="animate-fade-in" style={{ animationDelay: `${i * 50}ms` }}>
            <CardContent className="p-5">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                  <k.icon className="h-4 w-4 text-primary" />
                </div>
                <p className="text-xs font-medium text-muted-foreground">{k.title}</p>
              </div>
              <div className="mt-3">
                <ScoreRing value={k.value} />
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">{k.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {qualityItems.map((k, i) => (
          <Card key={k.title} className="animate-fade-in" style={{ animationDelay: `${(i + 4) * 50}ms` }}>
            <CardContent className="p-5">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary/60">
                  <k.icon className="h-4 w-4 text-secondary-foreground" />
                </div>
                <p className="text-xs font-medium text-muted-foreground">{k.title}</p>
              </div>
              <div className="mt-3">
                <ScoreRing value={k.value} invert={"invert" in k && k.invert} />
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">{k.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
