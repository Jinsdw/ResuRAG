import { DEFAULT_SUGGESTIONS } from '../constants/defaultSuggestions';
import { withFingerprintHeaders } from '../utils/fingerprint';
import { GENERATION_BASE } from './api';

export interface SuggestionsResponse {
  suggestions: string[];
}

export async function fetchDefaultSuggestions(): Promise<string[]> {
  const response = await fetch(`${GENERATION_BASE}/api/v1/suggestions/default`, {
    headers: withFingerprintHeaders(),
  });

  if (!response.ok) {
    throw new Error('获取默认推荐问题失败');
  }

  const data = (await response.json()) as SuggestionsResponse;
  return data.suggestions?.length ? data.suggestions : [...DEFAULT_SUGGESTIONS];
}

export async function fetchSuggestions(sessionId: string): Promise<string[]> {
  const response = await fetch(`${GENERATION_BASE}/api/v1/suggestions`, {
    method: 'POST',
    headers: withFingerprintHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    throw new Error('获取推荐问题失败');
  }

  const data = (await response.json()) as SuggestionsResponse;
  return data.suggestions?.length ? data.suggestions : [...DEFAULT_SUGGESTIONS];
}
