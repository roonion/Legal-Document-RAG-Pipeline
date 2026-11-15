/**
 * Catch-all proxy: forwards /api/v1/* from the browser
 * to the FastAPI backend inside Docker (http://api:8000).
 */

const BACKEND =
  process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000";

async function proxy(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const target = `${BACKEND}/api/v1/${path.join("/")}`;
  const url = new URL(target);

  const incoming = new URL(req.url);
  incoming.searchParams.forEach((v, k) => url.searchParams.set(k, v));

  const headers = new Headers(req.headers);
  headers.delete("host");
  // Undici (Node fetch) doesn't support the 'Expect' header and will throw.
  headers.delete("expect");

  const init: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = req.body;
    // @ts-expect-error Node fetch supports duplex
    init.duplex = "half";
  }

  const res = await fetch(url.toString(), init);

  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: Object.fromEntries(res.headers.entries()),
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
