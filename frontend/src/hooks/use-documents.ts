"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Document } from "@/types/document";

const ACTIVE = new Set(["pending", "extracting", "chunking", "embedding"]);

function hasActiveProcessing(docs: Document[] | undefined) {
  return docs?.some((d) => ACTIVE.has(d.status)) ?? false;
}

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: () => apiFetch<Document[]>("/api/v1/documents"),
    refetchInterval: (q) => (hasActiveProcessing(q.state.data) ? 2000 : false),
  });
}
