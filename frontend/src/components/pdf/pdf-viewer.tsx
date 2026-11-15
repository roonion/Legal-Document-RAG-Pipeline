"use client";

import dynamic from "next/dynamic";

import type { Citation } from "@/types/chat";

const PdfViewerInner = dynamic(() => import("./pdf-viewer-inner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[480px] items-center justify-center rounded-xl border border-dashed border-border bg-card text-sm text-muted-foreground">
      Loading PDF viewer...
    </div>
  ),
});

export function PdfViewer({
  documentUrl,
  highlights,
  selectedCitation,
}: {
  documentUrl: string;
  highlights?: Citation[];
  selectedCitation?: Citation | null;
}) {
  return (
    <PdfViewerInner
      documentUrl={documentUrl}
      highlights={highlights}
      selectedCitation={selectedCitation}
    />
  );
}
