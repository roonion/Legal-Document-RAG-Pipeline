"use client";

import { usePathname } from "next/navigation";

const breadcrumbMap: Record<string, string> = {
  "/dashboard": "Home",
  "/dashboard/chat": "AI Chat",
  "/dashboard/documents": "Document Library",
  "/dashboard/pipeline": "Processing Pipeline",
  "/dashboard/evaluation": "Model Evaluation",
};

export function Header({ title }: { title: string }) {
  const pathname = usePathname();
  const crumb = breadcrumbMap[pathname] ?? title;

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card/80 px-6 backdrop-blur-sm">
      <div>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        {crumb !== title && (
          <p className="text-xs text-muted-foreground">{crumb}</p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-1.5">
          <span className="h-2 w-2 rounded-full bg-success" />
          <span className="text-xs font-medium text-secondary-foreground">API Connected</span>
        </div>
      </div>
    </header>
  );
}
