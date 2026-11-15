/** API base URL for FastAPI backend. */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const ROUTES = {
  dashboard: "/dashboard",
  chat: "/dashboard/chat",
  documents: "/dashboard/documents",
  pipeline: "/dashboard/pipeline",
  evaluation: "/dashboard/evaluation",
} as const;
