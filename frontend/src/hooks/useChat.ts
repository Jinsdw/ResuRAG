import { useCallback, useState } from 'react';
import type { ChatMessage, DebugSettings, Session } from '../types';
import { streamGenerate } from '../services/generationService';

export function useChat(
  activeSession: Session | null,
  updateSession: (id: string, updater: (session: Session) => Session) => void,
  refreshSessions: (sessionId?: string) => Promise<void>,
  debug: DebugSettings,
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
        let content = '';
        let reasoning = '';
        const patchAssistant = (
          patch: Partial<Pick<ChatMessage, 'content' | 'reasoning' | 'citations' | 'pipelineStep' | 'statusMessage'>>,
        ) => {
          updateSession(sessionId, (session) => ({
            ...session,
            messages: session.messages.map((msg) =>
              msg.id === assistantId ? { ...msg, ...patch } : msg,
            ),
          }));
        };

        for await (const event of streamGenerate(query.trim(), sessionId, {
          userMessageId: userMessage.id,
          assistantMessageId: assistantId,
          citations: [],
          topK: debug.topK,
          similarityThreshold: debug.similarityThreshold,
        })) {
          if (event.type === 'status') {
            patchAssistant({
              pipelineStep: event.step,
              statusMessage: event.message,
            });
          } else if (event.type === 'citations') {
            patchAssistant({ citations: event.citations });
          } else if (event.type === 'content') {
            content += event.content;
            patchAssistant({ content, reasoning, statusMessage: undefined });
          } else if (event.type === 'reasoning') {
            reasoning += event.content;
            patchAssistant({ reasoning, content });
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        }

        updateSession(sessionId, (session) => ({
          ...session,
          messages: session.messages.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  isStreaming: false,
                  pipelineStep: undefined,
                  statusMessage: undefined,
                }
              : msg,
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
                  pipelineStep: undefined,
                  statusMessage: undefined,
                  citations: msg.citations ?? [],
                }
              : msg,
          ),
        }));
      } finally {
        setSending(false);
      }
    },
    [activeSession, sending, updateSession, refreshSessions, debug.topK, debug.similarityThreshold],
  );

  return { sending, sendMessage };
}
