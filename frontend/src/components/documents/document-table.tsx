"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { FileText, Trash2, Clock, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { PipelineStepper, statusToStepIndex } from "@/components/documents/pipeline-stepper";
import { Button } from "@/components/ui/button";
import type { Document } from "@/types/document";

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof CheckCircle2; className: string; label: string }> = {
    completed: { icon: CheckCircle2, className: "bg-success/10 text-success", label: "Ready" },
    failed: { icon: AlertCircle, className: "bg-danger/10 text-danger", label: "Failed" },
    pending: { icon: Clock, className: "bg-warning/10 text-warning", label: "Pending" },
  };
  const fallback = { icon: Loader2, className: "bg-info/10 text-info", label: "Processing" };
  const c = config[status] ?? fallback;
  const Icon = c.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${c.className}`}>
      <Icon className={`h-3 w-3 ${status === "completed" || status === "failed" || status === "pending" ? "" : "animate-spin"}`} />
      {c.label}
    </span>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

const columnHelper = createColumnHelper<Document>();

function useColumns() {
  const queryClient = useQueryClient();

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/v1/documents/${id}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch {
      /* swallow */
    }
  };

  return [
    columnHelper.accessor("filename", {
      header: "Document",
      cell: (info) => (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <FileText className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-medium text-foreground">{info.getValue()}</span>
        </div>
      ),
    }),
    columnHelper.accessor("status", {
      header: "Pipeline",
      cell: (info) => (
        <PipelineStepper
          activeIndex={statusToStepIndex(info.getValue())}
          failed={info.getValue() === "failed"}
        />
      ),
    }),
    columnHelper.accessor("status", {
      id: "statusLabel",
      header: "Status",
      cell: (info) => <StatusBadge status={info.getValue()} />,
    }),
    columnHelper.accessor("created_at", {
      header: "Added",
      cell: (info) => (
        <span className="text-xs text-muted-foreground">{formatDate(info.getValue())}</span>
      ),
    }),
    columnHelper.display({
      id: "actions",
      header: "",
      cell: (info) => (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => handleDelete(info.row.original.id)}
          className="h-8 w-8 text-muted-foreground hover:text-danger"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    }),
  ];
}

export function DocumentTable({ data }: { data: Document[] }) {
  const columns = useColumns();
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!data.length) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-foreground">No documents yet</h3>
        <p className="mt-1 max-w-[240px] text-xs text-muted-foreground">
          Upload your first PDF above to get started. It will appear here once processing begins.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-sm">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-border bg-secondary/50">
              {hg.headers.map((h) => (
                <th key={h.id} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row, idx) => (
            <tr
              key={row.id}
              className="border-b border-border/50 transition-colors hover:bg-secondary/30 animate-fade-in"
              style={{ animationDelay: `${idx * 30}ms` }}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 align-middle">
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
