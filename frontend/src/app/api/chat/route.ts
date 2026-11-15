import { API_BASE } from "@/lib/constants";

/**
 * Proxy FastAPI SSE → AI SDK UI message stream (v1 protocol).
 * @see https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
 */

function flattenUiMessages(payload: unknown): { role: string; content: string }[] {
  const raw = (payload as { messages?: unknown[] })?.messages;
  if (!Array.isArray(raw)) return [];
  return raw.map((m) => {
    const role = m && typeof (m as { role?: string }).role === "string" ? (m as { role: string }).role : "user";
    let content = "";
    const parts = (m as { parts?: { type: string; text?: string }[] }).parts;
    if (Array.isArray(parts)) {
      for (const p of parts) {
        if (p.type === "text" && p.text) content += p.text;
      }
    }
    const c = (m as { content?: string }).content;
    if (typeof c === "string" && content === "") content = c;
    return { role, content };
  });
}

export async function POST(req: Request) {
  const json = await req.json();
  const messages = flattenUiMessages(json);
  const body = JSON.stringify({ messages, stream: true });

  const res = await fetch(`${API_BASE}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body,
  });

  if (!res.ok) {
    return new Response(await res.text(), { status: res.status });
  }

  const messageId = crypto.randomUUID();
  const textId = `text_${messageId}`;

  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      const send = (obj: object) => controller.enqueue(enc.encode(`data: ${JSON.stringify(obj)}\n\n`));

      send({ type: "start", messageId });
      send({ type: "text-start", id: textId });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data:")) continue;
            const data = trimmed.slice(5).trim();
            if (data === "[DONE]") continue;
            if (!data) continue;

            let ev: Record<string, unknown>;
            try {
              ev = JSON.parse(data) as Record<string, unknown>;
            } catch {
              continue;
            }

            const t = ev.type as string;
            if (t === "text-delta") {
              const delta =
                (typeof ev.textDelta === "string" && ev.textDelta) ||
                (typeof ev.delta === "string" && ev.delta) ||
                "";
              if (delta) {
                send({ type: "text-delta", id: textId, delta });
              }
            } else if (t === "citations") {
              const citations = (ev.citations ?? []) as Array<{
                id?: string | number;
                document_id?: string;
                chunk_id?: string;
                text?: string;
              }>;
              for (const c of citations) {
                send({
                  type: "source-url",
                  sourceId: `citation-${c.id ?? ""}`,
                  url: c.document_id
                    ? `/api/pdf/${c.document_id}`
                    : "",
                  title: (c.text ?? "").slice(0, 300),
                  providerMetadata: {
                    citation: {
                      document_id: c.document_id ?? "",
                      chunk_id: c.chunk_id ?? "",
                      text: c.text ?? "",
                    },
                  },
                });
              }
            } else if (t === "meta") {
              /* meta events are informational; v1 has no matching type */
            }
          }
        }
      } finally {
        send({ type: "text-end", id: textId });
        send({ type: "finish" });
        controller.enqueue(enc.encode("data: [DONE]\n\n"));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      "x-vercel-ai-ui-message-stream": "v1",
    },
  });
}
