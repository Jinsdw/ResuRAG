export interface Citation {
  index: number;
  chunk_id: string;
  source_file_name: string;
  source_page: number;
  score: number;
  content: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  timestamp: number;
}

export interface Session {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface SearchResult {
  chunk_id: string;
  content: string;
  file_uuid: string;
  source_file_name: string;
  source_page: number;
  score: number;
  metadata: Record<string, unknown>;
}

export interface DebugSettings {
  similarityThreshold: number;
  topK: number;
}

export type StreamEvent =
  | { type: 'content'; content: string }
  | { type: 'reasoning'; content: string }
  | { type: 'done' }
  | { type: 'error'; message: string };
