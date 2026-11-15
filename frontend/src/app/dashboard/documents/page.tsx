"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { CheckCircle2, AlertCircle } from "lucide-react";

import { Header } from "@/components/layout/header";
import { DocumentTable } from "@/components/documents/document-table";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { useDocuments } from "@/hooks/use-documents";

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useDocuments();
  const [uploadState, setUploadState] = useState<{
    type: "idle" | "uploading" | "success" | "error";
    message?: string;
  }>({ type: "idle" });

  const onAccepted = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;
      setUploadState({ type: "uploading", message: `Uploading "${file.name}"...` });
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await fetch(`/api/v1/documents/upload`, {
          method: "POST",
          body: fd,
        });
        if (!res.ok) {
          throw new Error(await res.text());
        }
        await queryClient.invalidateQueries({ queryKey: ["documents"] });
        setUploadState({
          type: "success",
          message: `"${file.name}" uploaded successfully. Processing has started.`,
        });
        setTimeout(() => setUploadState({ type: "idle" }), 5000);
      } catch (e) {
        setUploadState({
          type: "error",
          message: e instanceof Error ? e.message : "Upload failed. Is the API running?",
        });
      }
    },
    [queryClient],
  );

  return (
    <>
      <Header title="Documents" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-6">
          <UploadDropzone
            onAccepted={onAccepted}
            isUploading={uploadState.type === "uploading"}
          />

          {uploadState.type === "success" && (
            <div className="flex items-center gap-2 animate-fade-in rounded-lg border border-success/30 bg-success/5 px-4 py-3">
              <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
              <p className="text-sm text-success">{uploadState.message}</p>
            </div>
          )}

          {uploadState.type === "uploading" && (
            <div className="flex items-center gap-2 animate-fade-in rounded-lg border border-info/30 bg-info/5 px-4 py-3">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-info border-t-transparent shrink-0" />
              <p className="text-sm text-info">{uploadState.message}</p>
            </div>
          )}

          {uploadState.type === "error" && (
            <div className="flex items-center gap-2 animate-fade-in rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
              <AlertCircle className="h-4 w-4 text-danger shrink-0" />
              <p className="text-sm text-danger">{uploadState.message}</p>
            </div>
          )}

          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
              <AlertCircle className="h-4 w-4 text-danger shrink-0" />
              <p className="text-sm text-danger">
                Could not load documents. Is the API running?
              </p>
            </div>
          )}

          {data && <DocumentTable data={data} />}
        </div>
      </main>
    </>
  );
}
