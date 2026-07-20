import type { ChatMessage, Citation, SessionMeta } from '../types';
import { GENERATION_BASE, request } from './api';

interface SessionRecordResponse {
  session_id: string;
  subject: string;
  created_at: number;
  updated_at: number;
}

interface SessionListResponse {
  total: number;
  sessions: SessionRecordResponse[];
}

interface ChatMessageRecordResponse {
  message_id: string;
  session_id: string;
  role: string;
  content: string;
  reasoning?: string | null;
  citations?: Citation[] | null;
  created_at: number;
}

interface ChatMessageListResponse {
  session_id: string;
  total: number;
  messages: ChatMessageRecordResponse[];
}

function toSessionMeta(record: SessionRecordResponse): SessionMeta {
  return {
    id: record.session_id,
    title: record.subject,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
    persisted: true,
  };
}

function toChatMessage(record: ChatMessageRecordResponse): ChatMessage {
  return {
    id: record.message_id,
    role: record.role as ChatMessage['role'],
    content: record.content,
    reasoning: record.reasoning ?? undefined,
    citations: record.citations ?? undefined,
    timestamp: record.created_at,
  };
}

let sessionsCache: SessionMeta[] | null = null;
let inflightSessionsRequest: Promise<SessionMeta[]> | null = null;

export function invalidateSessionsCache() {
  sessionsCache = null;
}

async function requestSessions(): Promise<SessionMeta[]> {
  if (inflightSessionsRequest) {
    return inflightSessionsRequest;
  }

  inflightSessionsRequest = request<SessionListResponse>(`${GENERATION_BASE}/api/v1/sessions`)
    .then((data) => {
      sessionsCache = data.sessions.map(toSessionMeta);
      return sessionsCache;
    })
    .finally(() => {
      inflightSessionsRequest = null;
    });

  return inflightSessionsRequest;
}

export async function fetchSessions(options?: { force?: boolean }): Promise<SessionMeta[]> {
  if (!options?.force && sessionsCache) {
    return sessionsCache;
  }
  return requestSessions();
}

export async function fetchSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const data = await request<ChatMessageListResponse>(
    `${GENERATION_BASE}/api/v1/sessions/${sessionId}/messages`,
  );
  return data.messages.map(toChatMessage);
}

export async function deleteSessionRemote(sessionId: string): Promise<void> {
  await request<{ ok: boolean }>(`${GENERATION_BASE}/api/v1/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  invalidateSessionsCache();
}

export function mergeSessionMetas(
  prev: SessionMeta[],
  remoteSessions: SessionMeta[],
): SessionMeta[] {
  const remoteIds = new Set(remoteSessions.map((item) => item.id));
  const localDrafts = prev.filter((item) => !item.persisted && !remoteIds.has(item.id));
  const mergedRemote = remoteSessions.map((remote) => {
    const local = prev.find((item) => item.id === remote.id);
    if (!local || local.persisted === false) return remote;
    return {
      ...remote,
      title: local.updatedAt > remote.updatedAt ? local.title : remote.title,
    };
  });
  return [...localDrafts, ...mergedRemote];
}
