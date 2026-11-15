"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import {
  LayoutDashboard,
  MessageSquareText,
  FileText,
  Workflow,
  BarChart3,
  Scale,
} from "lucide-react";

const links = [
  { href: ROUTES.dashboard, label: "Overview", icon: LayoutDashboard },
  { href: ROUTES.chat, label: "Chat", icon: MessageSquareText },
  { href: ROUTES.documents, label: "Documents", icon: FileText },
  { href: ROUTES.pipeline, label: "Pipeline", icon: Workflow },
  { href: ROUTES.evaluation, label: "Evaluation", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-64 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-3 border-b border-border px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Scale className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-foreground">Legal RAG</p>
          <p className="text-xs text-muted-foreground">Document Intelligence</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
        <p className="mb-2 px-3 text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
          Navigation
        </p>
        {links.map((l) => {
          const active = pathname === l.href;
          const Icon = l.icon;
          return (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                active
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon
                className={cn(
                  "h-[18px] w-[18px] shrink-0 transition-colors",
                  active ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground",
                )}
              />
              {l.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-4 py-4">
        <div className="rounded-lg bg-secondary px-3 py-3">
          <p className="text-xs font-medium text-secondary-foreground">System Status</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-success" />
            <span className="text-xs text-muted-foreground">All services running</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
