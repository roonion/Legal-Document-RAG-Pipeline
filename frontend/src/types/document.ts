export type ProcessingStatus =
  | "pending"
  | "extracting"
  | "chunking"
  | "embedding"
  | "completed"
  | "failed";

export interface Document {
  id: string;
  filename: string;
  content_hash: string;
  status: string;
  created_at: string;
  updated_at: string;
  error_message?: string | null;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  vector_db_id?: string | null;
}
