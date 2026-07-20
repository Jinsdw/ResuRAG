import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChatMessage, Session, SessionMeta } from '../types';
import {
  deleteSessionRemote,
  fetchSessionMessages,
  fetchSessions,
  invalidateSessionsCache,
  mergeSessionMetas,
} from '../services/sessionService';

const ACTIVE_KEY = 'resurag_active_session';

function createLocalSession(): SessionMeta {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: '新对话',
    createdAt: now,
    updatedAt: now,
    persisted: false,
  };
}

export function useSessions() {
  const [sessionMetas, setSessionMetas] = useState<SessionMeta[]>([]);
  const [messagesById, setMessagesById] = useState<Record<string, ChatMessage[]>>({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() =>
    localStorage.getItem(ACTIVE_KEY),
  );
  const [loading, setLoading] = useState(true);

  const metasRef = useRef(sessionMetas);
  metasRef.current = sessionMetas;
  const messagesRef = useRef(messagesById);
  messagesRef.current = messagesById;

  const sessions = useMemo<Session[]>(
    () =>
      [...sessionMetas]
        .sort((a, b) => b.updatedAt - a.updatedAt)
        .map((meta) => ({
          ...meta,
          messages: messagesById[meta.id] ?? [],
        })),
    [sessionMetas, messagesById],
  );

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null;

  const applyRemoteSessions = useCallback((remoteSessions: SessionMeta[]) => {
    setSessionMetas((prev) => mergeSessionMetas(prev, remoteSessions));
  }, []);

  const loadSessionMessages = useCallback(async (sessionId: string) => {
    try {
      const messages = await fetchSessionMessages(sessionId);
      setMessagesById((prev) => {
        const next = { ...prev, [sessionId]: messages };
        messagesRef.current = next;
        return next;
      });
    } catch {
      setMessagesById((prev) => {
        const next = { ...prev, [sessionId]: [] };
        messagesRef.current = next;
        return next;
      });
    }
  }, []);

  const refreshSessions = useCallback(
    async (sessionId?: string) => {
      invalidateSessionsCache();
      const remoteSessions = await fetchSessions({ force: true });
      applyRemoteSessions(remoteSessions);

      const targetId = sessionId ?? activeSessionId;
      if (!targetId) return;

      const meta = remoteSessions.find((item) => item.id === targetId);
      if (meta?.persisted) {
        await loadSessionMessages(targetId);
      }
    },
    [activeSessionId, applyRemoteSessions, loadSessionMessages],
  );

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const remoteSessions = await fetchSessions();
        if (cancelled) return;

        applyRemoteSessions(remoteSessions);
        setActiveSessionId((current) => {
          const remoteIds = new Set(remoteSessions.map((item) => item.id));
          if (current && remoteIds.has(current)) return current;
          return remoteSessions[0]?.id ?? null;
        });
      } catch {
        if (!cancelled && sessionMetas.length === 0) {
          const session = createLocalSession();
          setSessionMetas([session]);
          setActiveSessionId(session.id);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applyRemoteSessions]);

  useEffect(() => {
    if (loading) return;
    if (sessionMetas.length === 0) {
      const session = createLocalSession();
      setSessionMetas([session]);
      setActiveSessionId(session.id);
      return;
    }
    if (!activeSessionId || !sessionMetas.some((item) => item.id === activeSessionId)) {
      setActiveSessionId(sessionMetas[0].id);
    }
  }, [loading, sessionMetas, activeSessionId]);

  useEffect(() => {
    if (!activeSessionId || loading) return;
    const meta = metasRef.current.find((item) => item.id === activeSessionId);
    if (meta?.persisted) {
      void loadSessionMessages(activeSessionId);
    }
  }, [activeSessionId, loading, loadSessionMessages]);

  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem(ACTIVE_KEY, activeSessionId);
    }
  }, [activeSessionId]);

  const createNewSession = useCallback(() => {
    const session = createLocalSession();
    setSessionMetas((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
    return { ...session, messages: [] };
  }, []);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const updateSession = useCallback((id: string, updater: (session: Session) => Session) => {
    const meta = metasRef.current.find((item) => item.id === id);
    if (!meta) return;

    const current: Session = {
      ...meta,
      messages: messagesRef.current[id] ?? [],
    };
    const updated = updater(current);

    const nextMessages = { ...messagesRef.current, [id]: updated.messages };
    messagesRef.current = nextMessages;
    setMessagesById(nextMessages);

    setSessionMetas((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              title: updated.title,
              updatedAt: updated.updatedAt,
              persisted: item.persisted,
            }
          : item,
      ),
    );
  }, []);

  const deleteSession = useCallback(
    async (id: string) => {
      const meta = metasRef.current.find((item) => item.id === id);
      if (meta?.persisted) {
        try {
          await deleteSessionRemote(id);
        } catch {
          // 服务端已不存在时仍清理本地
        }
      }

      setSessionMetas((prev) => {
        const next = prev.filter((item) => item.id !== id);
        if (activeSessionId === id) {
          setActiveSessionId(next[0]?.id ?? null);
        }
        return next;
      });

      setMessagesById((prev) => {
        const next = { ...prev };
        delete next[id];
        messagesRef.current = next;
        return next;
      });
    },
    [activeSessionId],
  );

  return {
    sessions,
    activeSession,
    activeSessionId,
    loading,
    createNewSession,
    selectSession,
    updateSession,
    deleteSession,
    refreshSessions,
  };
};
