import { useCallback, useState } from 'react';
import type { ChatMessage, Citation, DebugSettings, SearchResult, Session } from '../types';
import { streamGenerate } from '../services/generationService';
import { searchDocuments } from '../services/retrievalService';

function toCitations(results: SearchResult[]): Citation[] {
  return results.map((item, index) => ({
    index: index + 1,
    chunk_id: item.chunk_id,
    source_file_name: item.source_file_name,
    source_page: item.source_page,
    score: item.score,
    content: item.content,
  }));
}

export function useChat(
  activeSession: Session | null,
  updateSession: (id: string, updater: (session: Session) => Session) => void,
  debug: DebugSettings,
  refreshSessions: (sessionId?: string) => Promise<void>,
) {
  const [sending, setSending] = useState(false);

  const sendMessage = useCallback(
    async (query: string) => {
      if (!activeSession || !query.trim() || sending) return;

      const sessionId = activeSession.id;
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query.trim(),
        timestamp: Date.now(),
      };

      const assistantId = crypto.randomUUID();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        isStreaming: true,
        timestamp: Date.now(),
      };

      updateSession(sessionId, (session) => {
        const title =
          session.messages.length === 0 ? query.trim().slice(0, 30) : session.title;
        return {
          ...session,
          title,
          updatedAt: Date.now(),
          messages: [...session.messages, userMessage, assistantMessage],
        };
      });

      setSending(true);
      try {
        const results = await searchDocuments({
          query: query.trim(),
          topK: debug.topK,
          similarityThreshold: debug.similarityThreshold,
        });

        const citations = toCitations(results);

        updateSession(sessionId, (session) => ({
          ...session,
          messages: session.messages.map((msg) =>
            msg.id === assistantId ? { ...msg, citations } : msg,
          ),
        }));

        let content = '';
        let reasoning = '';
        for await (const event of streamGenerate(query.trim(), results, sessionId, {
          userMessageId: userMessage.id,
          assistantMessageId: assistantId,
          citations,
        })) {
          if (event.type === 'content') {
            content += event.content;
            updateSession(sessionId, (session) => ({
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === assistantId ? { ...msg, content, reasoning } : msg,
              ),
            }));
          } else if (event.type === 'reasoning') {
            reasoning += event.content;
            updateSession(sessionId, (session) => ({
              ...session,
              messages: session.messages.map((msg) =>
                msg.id === assistantId ? { ...msg, content, reasoning } : msg,
              ),
            }));
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        }

        updateSession(sessionId, (session) => ({
          ...session,
          messages: session.messages.map((msg) =>
            msg.id === assistantId ? { ...msg, isStreaming: false } : msg,
          ),
        }));
        await refreshSessions(sessionId);
      } catch (error) {
        const message = error instanceof Error ? error.message : '发送失败';
        updateSession(sessionId, (session) => ({
          ...session,
          messages: session.messages.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: `抱歉，生成回答时出错：${message}`,
                  isStreaming: false,
                  citations: msg.citations ?? [],
                }
              : msg,
          ),
        }));
      } finally {
        setSending(false);
      }
    },
    [activeSession, debug, sending, updateSession, refreshSessions],
  );

  return { sending, sendMessage };
}
