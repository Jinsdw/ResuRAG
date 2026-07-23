import { useCallback, useEffect, useState } from 'react';
import { DEFAULT_SUGGESTIONS } from '../constants/defaultSuggestions';
import { fetchDefaultSuggestions, fetchSuggestions } from '../services/suggestionService';
import type { Session } from '../types';

export function useSuggestedQuestions(activeSession: Session | null, sending: boolean) {
  const [suggestions, setSuggestions] = useState<string[]>([...DEFAULT_SUGGESTIONS]);
  const [loading, setLoading] = useState(false);

  const loadDefaultSuggestions = useCallback(async () => {
    try {
      const items = await fetchDefaultSuggestions();
      setSuggestions(items);
    } catch {
      setSuggestions([...DEFAULT_SUGGESTIONS]);
    }
  }, []);

  const refreshSuggestions = useCallback(async (sessionId: string, hasMessages: boolean) => {
    if (!hasMessages) {
      await loadDefaultSuggestions();
      return;
    }

    setLoading(true);
    try {
      const items = await fetchSuggestions(sessionId);
      setSuggestions(items);
    } catch {
      await loadDefaultSuggestions();
    } finally {
      setLoading(false);
    }
  }, [loadDefaultSuggestions]);

  useEffect(() => {
    void loadDefaultSuggestions();
  }, [loadDefaultSuggestions]);

  useEffect(() => {
    if (!activeSession) {
      void loadDefaultSuggestions();
      return;
    }

    if (activeSession.messages.length === 0) {
      void loadDefaultSuggestions();
      return;
    }

    if (!sending) {
      void refreshSuggestions(activeSession.id, true);
    }
  }, [activeSession?.id, activeSession?.messages.length, sending, refreshSuggestions, loadDefaultSuggestions]);

  return { suggestions, loading, refreshSuggestions };
}
