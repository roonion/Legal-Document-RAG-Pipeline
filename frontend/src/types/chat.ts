export interface Citation {
  id: string;
  document_id: string;
  chunk_id?: string;
  text: string;
  /** Bounding boxes for PDF highlighting (viewport-independent coordinates). */
  rects?: Array<{ page: number; x: number; y: number; width: number; height: number }>;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
}
