import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { DebugSettings, KnowledgeFile, Session, UploadResult } from '../types';
import { useChat } from '../hooks/useChat';
import { useKnowledgeBase } from '../hooks/useKnowledgeBase';
import { useSessions } from '../hooks/useSessions';

interface AppContextValue {
  sessions: Session[];
  activeSession: Session | null;
  activeSessionId: string | null;
  createNewSession: () => Session;
  selectSession: (id: string) => void;
  deleteSession: (id: string) => void;
  files: KnowledgeFile[];
  filesLoading: boolean;
  uploading: boolean;
  uploadFile: (file: File) => Promise<UploadResult>;
  refreshFiles: () => Promise<void>;
  debug: DebugSettings;
  setDebug: (patch: Partial<DebugSettings>) => void;
  sending: boolean;
  sendMessage: (query: string) => Promise<void>;
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
  } = useSessions();

  const { files, loading: filesLoading, uploading, refresh, upload } = useKnowledgeBase();

  const [debug, setDebugState] = useState<DebugSettings>({
    selectedFileUuid: null,
    similarityThreshold: 0.3,
    topK: 10,
  });

  const setDebug = (patch: Partial<DebugSettings>) => {
    setDebugState((prev) => ({ ...prev, ...patch }));
  };

  const { sending, sendMessage } = useChat(activeSession, updateSession, debug);

  const value = useMemo<AppContextValue>(
    () => ({
      sessions,
      activeSession,
      activeSessionId,
      createNewSession,
      selectSession,
      deleteSession,
      files,
      filesLoading,
      uploading,
      uploadFile: upload,
      refreshFiles: refresh,
      debug,
      setDebug,
      sending,
      sendMessage,
    }),
    [
      sessions,
      activeSession,
      activeSessionId,
      createNewSession,
      selectSession,
      deleteSession,
      files,
      filesLoading,
      uploading,
      upload,
      refresh,
      debug,
      sending,
      sendMessage,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppProvider');
  return ctx;
}
