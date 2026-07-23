import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import type { DebugSettings, Session } from '../types';
import { useChat } from '../hooks/useChat';
import { useSuggestedQuestions } from '../hooks/useSuggestedQuestions';
import { useSessions } from '../hooks/useSessions';

interface AppContextValue {
  sessions: Session[];
  activeSession: Session | null;
  activeSessionId: string | null;
  createNewSession: () => Session;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => Promise<void>;
  debug: DebugSettings;
  setDebug: (patch: Partial<DebugSettings>) => void;
  sending: boolean;
  sendMessage: (query: string) => Promise<void>;
  suggestions: string[];
  suggestionsLoading: boolean;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const {
    sessions,
    activeSession,
    activeSessionId,
    createNewSession,
    selectSession,
    updateSession,
    deleteSession,
    refreshSessions,
  } = useSessions();

  const [debug, setDebugState] = useState<DebugSettings>({
    similarityThreshold: 0.3,
    topK: 5,
  });

  const setDebug = (patch: Partial<DebugSettings>) => {
    setDebugState((prev) => ({ ...prev, ...patch }));
  };

  const suggestionRefreshRef = useRef<(sessionId: string) => void>(() => {});

  const { sending, sendMessage } = useChat(
    activeSession,
    updateSession,
    refreshSessions,
    debug,
    (sessionId) => suggestionRefreshRef.current(sessionId),
  );

  const { suggestions, loading: suggestionsLoading, refreshSuggestions } =
    useSuggestedQuestions(activeSession, sending);

  suggestionRefreshRef.current = (sessionId) => {
    void refreshSuggestions(sessionId, true);
  };

  const value = useMemo<AppContextValue>(
    () => ({
      sessions,
      activeSession,
      activeSessionId,
      createNewSession,
      selectSession,
      deleteSession,
      debug,
      setDebug,
      sending,
      sendMessage,
      suggestions,
      suggestionsLoading,
    }),
    [
      sessions,
      activeSession,
      activeSessionId,
      createNewSession,
      selectSession,
      deleteSession,
      debug,
      sending,
      sendMessage,
      suggestions,
      suggestionsLoading,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}
