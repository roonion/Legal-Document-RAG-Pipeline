"use client";

import { useChat } from "@ai-sdk/react";
import { useMemo, useEffect, useRef } from "react";
import type { UIMessage } from "ai";
import { Send, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MessageList } from "@/components/chat/message-list";

import type { Citation } from "@/types/chat";

function citationsFromMessages(messages: UIMessage[]): Citation[] {
  const last = messages[messages.length - 1];
  if (!last || last.role !== "assistant" || !Array.isArray(last.parts)) return [];

  const citations: Citation[] = [];
  for (const p of last.parts) {
    if (p.type === "source-url") {
      const src = p as {
        type: "source-url";
        sourceId: string;
        url: string;
        title?: string;
        providerMetadata?: Record<string, unknown>;
      };
      const meta = (
        src.providerMetadata as
          | Record<string, Record<string, string>>
          | undefined
      )?.citation;
      citations.push({
        id: src.sourceId ?? String(citations.length),
        document_id: meta?.document_id ?? "",
        chunk_id: meta?.chunk_id,
        text: meta?.text ?? src.title ?? "",
      });
    }
  }
  return citations;
}

export function ChatPanel({
  onCitationsReceived,
  onCitationClick,
}: {
  onCitationsReceived?: (citations: Citation[]) => void;
  onCitationClick?: (citation: Citation, index: number) => void;
}) {
  const { messages, sendMessage, status } = useChat();
  const citations = useMemo(() => citationsFromMessages(messages), [messages]);
  const busy = status === "streaming" || status === "submitted";
  const hasMessages = messages.length > 0;
  const prevCitationsRef = useRef<Citation[]>([]);

  useEffect(() => {
    if (
      citations.length > 0 &&
      citations !== prevCitationsRef.current &&
      onCitationsReceived
    ) {
      prevCitationsRef.current = citations;
      onCitationsReceived(citations);
    }
  }, [citations, onCitationsReceived]);

  return (
    <div className="flex h-full min-h-[480px] flex-col rounded-xl border border-border bg-card shadow-sm">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {!hasMessages ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
              <Send className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mt-4 text-base font-semibold text-foreground">
              Ask about your documents
            </h3>
            <p className="mt-1 max-w-xs text-sm text-muted-foreground">
              Upload a legal document first, then ask questions here. 
              Answers will include citations from the source text.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {[
                "What are the key obligations?",
                "Summarize the termination clause",
                "What are the payment terms?",
              ].map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => sendMessage({ text: q })}
                  className="rounded-lg border border-border bg-secondary px-3 py-1.5 text-xs text-secondary-foreground transition-colors hover:bg-muted"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <MessageList messages={messages} citations={citations} isLoading={busy} onCitationClick={onCitationClick} />
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-border p-4">
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const form = e.currentTarget;
            const input = form.elements.namedItem("q") as HTMLInputElement;
            const text = input?.value?.trim();
            if (!text || busy) return;
            sendMessage({ text });
            input.value = "";
          }}
        >
          <input
            name="q"
            className="flex-1 rounded-lg border border-border bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 transition-all"
            placeholder="Ask a question about your documents..."
            disabled={busy}
            autoComplete="off"
          />
          <Button type="submit" disabled={busy} size="icon" className="h-10 w-10 shrink-0">
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          AI responses are grounded in your uploaded documents. Always verify important legal details.
        </p>
      </div>
    </div>
  );
}
