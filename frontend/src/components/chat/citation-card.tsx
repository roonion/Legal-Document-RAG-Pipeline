import type { Citation } from "@/types/chat";

/** Clickable citation; scrolls PDF viewer via react-pdf-highlighter-extended. */
export function CitationCard({
  citation,
  onSelect,
}: {
  citation: Citation;
  onSelect?: (c: Citation) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(citation)}
      className="w-full rounded border border-amber-200 bg-amber-50 p-2 text-left text-xs dark:border-amber-900 dark:bg-amber-950"
    >
      {citation.text.slice(0, 200)}
      {citation.text.length > 200 ? "…" : ""}
    </button>
  );
}
