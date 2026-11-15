"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileUp, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function UploadDropzone({
  onAccepted,
  isUploading,
}: {
  onAccepted?: (files: File[]) => void;
  isUploading?: boolean;
}) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      onAccepted?.(accepted);
    },
    [onAccepted],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "group relative cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200",
        isDragActive
          ? "border-primary bg-primary/5 scale-[1.01]"
          : "border-border bg-card hover:border-primary/50 hover:bg-primary/[0.02]",
        isUploading && "pointer-events-none opacity-60",
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div
          className={cn(
            "flex h-12 w-12 items-center justify-center rounded-xl transition-colors",
            isDragActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary",
          )}
        >
          {isUploading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : isDragActive ? (
            <FileUp className="h-6 w-6" />
          ) : (
            <Upload className="h-6 w-6" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            {isDragActive
              ? "Drop your PDF here"
              : isUploading
                ? "Uploading..."
                : "Drag & drop a PDF, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Supports PDF files up to 50MB. Documents are processed automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
