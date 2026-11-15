"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { FileText, BookOpen, X, Search } from "lucide-react";
import type { Citation } from "@/types/chat";

export default function PdfViewerInner({
  documentUrl,
  highlights,
  selectedCitation,
}: {
  documentUrl: string;
  highlights?: Citation[];
  selectedCitation?: Citation | null;
}) {
  const [showSelected, setShowSelected] = useState(true);
  const prevCitationRef = useRef<Citation | null>(null);

  useEffect(() => {
    if (selectedCitation && selectedCitation !== prevCitationRef.current) {
      prevCitationRef.current = selectedCitation;
      setShowSelected(true);
    }
  }, [selectedCitation]);

  const iframeSrc = useMemo(() => {
    if (!documentUrl) return "";
    if (selectedCitation?.text) {
      const words = selectedCitation.text.trim().split(/\s+/).slice(0, 6).join(" ");
      return `${documentUrl}#search=${encodeURIComponent(words)}`;
    }
    return documentUrl;
  }, [documentUrl, selectedCitation]);

  if (!documentUrl) {
    return (
      <div className="flex h-full min-h-[480px] flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 p-6 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-foreground">
          PDF Preview
        </h3>
        <p className="mt-1 max-w-[220px] text-xs text-muted-foreground">
          Ask a question in the chat — the source PDF will load here
          automatically when citations arrive.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Selected citation highlight banner */}
      {selectedCitation && showSelected && (
        <div className="animate-fade-in rounded-xl border border-accent/40 bg-accent/10 p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2 min-w-0">
              <Search className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-accent">
                  Viewing Source
                </p>
                <p className="mt-1 text-xs leading-relaxed text-foreground/80 line-clamp-4">
                  {selectedCitation.text}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowSelected(false)}
              className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      <iframe
        title="PDF"
        src={iframeSrc}
        className="h-full min-h-[480px] w-full rounded-xl border border-border bg-card"
      />

      {/* All citation snippets */}
      {highlights && highlights.length > 0 && !selectedCitation && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-3">
          <div className="flex items-center gap-2">
            <BookOpen className="h-3.5 w-3.5 text-accent" />
            <p className="text-xs font-semibold text-accent">
              {highlights.length} Source{highlights.length !== 1 ? "s" : ""} Found
            </p>
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            Click a citation in the chat to view its source passage here.
          </p>
        </div>
      )}
    </div>
  );
}
