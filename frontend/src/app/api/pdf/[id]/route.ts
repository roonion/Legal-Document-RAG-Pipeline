import { API_BASE } from "@/lib/constants";

/**
 * Proxy PDF bytes from the backend so the browser can render them
 * in an iframe without hitting CORS or Docker-internal hostnames.
 */
export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;

  const upstream = await fetch(`${API_BASE}/api/v1/documents/${id}/pdf`, {
    headers: { Accept: "application/pdf" },
  });

  if (!upstream.ok) {
    return new Response("PDF not found", { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Cache-Control": "private, max-age=3600",
    },
  });
}
