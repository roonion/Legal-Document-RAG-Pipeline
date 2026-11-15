import type { UIMessage } from "ai";
import { User, Bot, BookOpen, ExternalLink } from "lucide-react";

import type { Citation } from "@/types/chat";

function textFromMessage(m: UIMessage): string {
  if (!Array.isArray(m.parts)) return "";
  return m.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("");
}

export function MessageList({
  messages,
  citations,
  isLoading,
  onCitationClick,
}: {
  messages: UIMessage[];
  citations?: Citation[];
  isLoading?: boolean;
  onCitationClick?: (citation: Citation, index: number) => void;
}) {
  const last = messages[messages.length - 1];
  const showCitations = last?.role === "assistant" && citations && citations.length > 0;

  return (
    <div className="flex flex-col gap-4">
      {messages.map((m, idx) => {
        const isUser = m.role === "user";
        return (
          <div
            key={m.id}
            className={`flex gap-3 ${isUser ? "animate-slide-right" : "animate-slide-left"}`}
            style={{ animationDelay: `${idx * 30}ms` }}
          >
            <div
              className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                isUser
                  ? "bg-primary text-primary-foreground"
                  : "bg-accent/15 text-accent"
              }`}
            >
              {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-muted-foreground">
                {isUser ? "You" : "Legal AI"}
              </p>
              <div
                className={`mt-1 rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  isUser
                    ? "bg-primary/5 text-foreground"
                    : "bg-secondary text-foreground"
                }`}
              >
                <p className="whitespace-pre-wrap">{textFromMessage(m)}</p>
              </div>
            </div>
          </div>
        );
      })}

      {showCitations && (
        <div className="ml-11 animate-fade-in">
          <div className="rounded-xl border border-accent/30 bg-accent/5 p-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-accent" />
              <p className="text-xs font-semibold text-accent">
                Sources ({citations!.length})
              </p>
            </div>
            <ul className="mt-2 space-y-2">
              {citations!.map((c, i) => (
                <li
                  key={`${c.id}-${i}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onCitationClick?.(c, i)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") onCitationClick?.(c, i);
                  }}
                  className="group cursor-pointer rounded-lg bg-card p-2.5 text-xs leading-relaxed text-muted-foreground border border-border transition-all hover:border-accent/50 hover:bg-accent/5 hover:shadow-sm active:scale-[0.99]"
                >
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-accent/15 text-[10px] font-bold text-accent">
                      {i + 1}
                    </span>
                    <span className="flex-1">
                      {(c.text || "").slice(0, 250)}
                      {c.text && c.text.length > 250 ? "..." : ""}
                    </span>
                    <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 text-accent opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="ml-11 flex items-center gap-2 animate-fade-in">
          <div className="flex gap-1">
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse-soft" />
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse-soft" style={{ animationDelay: "200ms" }} />
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse-soft" style={{ animationDelay: "400ms" }} />
          </div>
          <p className="text-xs text-muted-foreground">Analyzing documents...</p>
        </div>
      )}
    </div>
  );
}
