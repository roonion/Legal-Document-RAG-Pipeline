"use client";

import { Header } from "@/components/layout/header";
import { useDocuments } from "@/hooks/use-documents";
import {
  Upload,
  FileSearch,
  Scissors,
  Cpu,
  Database,
  ArrowRight,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const stages = [
  {
    icon: Upload,
    label: "Upload",
    description: "PDF is uploaded to secure object storage (MinIO)",
  },
  {
    icon: FileSearch,
    label: "Parse",
    description: "Text and structure extracted using PyMuPDF",
  },
  {
    icon: Scissors,
    label: "Chunk",
    description: "Text split into overlapping semantic chunks",
  },
  {
    icon: Cpu,
    label: "Embed",
    description: "Dense vectors generated via BGE-small-en-v1.5",
  },
  {
    icon: Database,
    label: "Index",
    description: "Vectors stored in Qdrant for hybrid search",
  },
];

export default function PipelinePage() {
  const { data: docs } = useDocuments();
  const completed = docs?.filter((d) => d.status === "completed").length ?? 0;
  const processing = docs?.filter(
    (d) => !["completed", "failed"].includes(d.status),
  ).length ?? 0;
  const total = docs?.length ?? 0;

  return (
    <>
      <Header title="Processing Pipeline" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl space-y-8">
          <div className="animate-fade-in">
            <h2 className="text-xl font-semibold text-foreground">
              Document Ingestion Pipeline
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Every uploaded document passes through these 5 stages before it becomes searchable.
            </p>
          </div>

          {/* Stats */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="animate-fade-in">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-info/10">
                  <Database className="h-4 w-4 text-info" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{total}</p>
                  <p className="text-xs text-muted-foreground">Total</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in" style={{ animationDelay: "50ms" }}>
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-success/10">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{completed}</p>
                  <p className="text-xs text-muted-foreground">Indexed</p>
                </div>
              </CardContent>
            </Card>
            <Card className="animate-fade-in" style={{ animationDelay: "100ms" }}>
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-warning/10">
                  <Clock className="h-4 w-4 text-warning" />
                </div>
                <div>
                  <p className="text-lg font-bold text-foreground">{processing}</p>
                  <p className="text-xs text-muted-foreground">In Progress</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Pipeline visual */}
          <div className="space-y-3">
            {stages.map((stage, i) => (
              <div key={stage.label}>
                <div
                  className="animate-fade-in flex items-start gap-4 rounded-xl border border-border bg-card p-5 transition-shadow hover:shadow-md"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10">
                    <stage.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                        {i + 1}
                      </span>
                      <h3 className="text-sm font-semibold text-foreground">{stage.label}</h3>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                      {stage.description}
                    </p>
                  </div>
                </div>
                {i < stages.length - 1 && (
                  <div className="flex justify-center py-1">
                    <ArrowRight className="h-4 w-4 rotate-90 text-border" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
