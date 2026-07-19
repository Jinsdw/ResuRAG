import { useCallback, useEffect, useState } from 'react';
import type { Session } from '../types';

const STORAGE_KEY = 'resurag_sessions';
const ACTIVE_KEY = 'resurag_active_session';

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session[]) : [];
  } catch {
    return [];
  }
}

function createSession(): Session {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: '新对话',
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions());
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    const stored = localStorage.getItem(ACTIVE_KEY);
    const list = loadSessions();
    if (stored && list.some((s) => s.id === stored)) return stored;
    return list[0]?.id ?? null;
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem(ACTIVE_KEY, activeSessionId);
    }
  }, [activeSessionId]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null;

  const createNewSession = useCallback(() => {
    const session = createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
    return session;
  }, []);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const updateSession = useCallback((id: string, updater: (session: Session) => Session) => {
    setSessions((prev) =>
      prev.map((session) => (session.id === id ? updater(session) : session)),
    );
  }, []);

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (activeSessionId === id) {
          setActiveSessionId(next[0]?.id ?? null);
        }
        return next;
      });
    },
    [activeSessionId],
  );

  useEffect(() => {
    if (sessions.length === 0) {
      createNewSession();
    } else if (!activeSessionId) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions.length, activeSessionId, createNewSession]);

  return {
    sessions,
    activeSession,
    activeSessionId,
    createNewSession,
    selectSession,
    updateSession,
    deleteSession,
  };
}
