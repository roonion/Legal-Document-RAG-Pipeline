import type { Citation } from "@/types/chat";

export interface HighlightRect {
  id: string;
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
}

/** Map citation rects to flat highlight objects for custom rendering. */
export function citationToHighlights(c: Citation): HighlightRect[] {
  const rects = c.rects;
  if (!rects?.length) {
    return [];
  }
  return rects.map((r, i) => ({
    id: `${c.id}-${i}`,
    page: r.page,
    x: r.x,
    y: r.y,
    width: r.width,
    height: r.height,
    text: c.text || "",
  }));
}
