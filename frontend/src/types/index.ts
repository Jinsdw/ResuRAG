export interface Citation {
  index: number;
  chunk_id: string;
  source_file_name: string;
  source_page: number;
  score: number;
  content: string;
}

export type PipelineStep =
  | 'rewriting'
  | 'judging'
  | 'retrieving'
  | 'direct'
  | 'preparing'
  | 'generating';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  /** 模型思考过程（流式 reasoning） */
  reasoning?: string;
  /** 未定义表示检索中；空数组表示检索完成但无命中 */
  citations?: Citation[];
  isStreaming?: boolean;
  /** 生成流水线当前阶段（SSE status 事件） */
  pipelineStep?: PipelineStep;
  /** 生成流水线当前阶段文案 */
  statusMessage?: string;
  timestamp: number;
}

export interface SessionMeta {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  /** 是否已持久化到服务端 */
  persisted?: boolean;
}

export interface Session extends SessionMeta {
  messages: ChatMessage[];
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
  | { type: 'status'; step: PipelineStep; message: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'content'; content: string }
  | { type: 'reasoning'; content: string }
  | { type: 'done' }
  | { type: 'error'; message: string };
