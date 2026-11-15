import { CheckCircle2, XCircle } from "lucide-react";
import type { ProcessingStatus } from "@/types/document";

const steps = ["Upload", "Parse", "Chunk", "Embed", "Index"] as const;

export function statusToStepIndex(status: string): number {
  const s = status as ProcessingStatus;
  switch (s) {
    case "pending": return 0;
    case "extracting": return 1;
    case "chunking": return 2;
    case "embedding": return 3;
    // When fully completed, advance past the last step so all steps render as completed.
    case "completed": return steps.length;
    case "failed": return 0;
    default: return 0;
  }
}

export function PipelineStepper({
  activeIndex,
  failed,
}: {
  activeIndex: number;
  failed?: boolean;
}) {
  return (
    <div className="flex items-center gap-1">
      {steps.map((s, i) => {
        const isCompleted = !failed && i < activeIndex;
        const isCurrent = !failed && i === activeIndex;
        const isFailed = failed && i === 0;

        return (
          <div key={s} className="flex items-center gap-1">
            {i > 0 && (
              <div className={`h-px w-3 ${isCompleted ? "bg-success" : "bg-border"}`} />
            )}
            <div
              className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium transition-all ${
                isFailed
                  ? "bg-danger/10 text-danger"
                  : isCompleted
                    ? "bg-success/10 text-success"
                    : isCurrent
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground"
              }`}
            >
              {isFailed && <XCircle className="h-3 w-3" />}
              {isCompleted && <CheckCircle2 className="h-3 w-3" />}
              {s}
            </div>
          </div>
        );
      })}
    </div>
  );
}
