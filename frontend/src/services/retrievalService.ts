import type { SearchResult } from '../types';
import { RETRIEVAL_BASE, request } from './api';

interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

export async function searchDocuments(params: {
  query: string;
  topK?: number;
}): Promise<SearchResult[]> {
  const data = await request<SearchResponse>(`${RETRIEVAL_BASE}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: params.query,
      top_k: params.topK ?? 10,
    }),
  });
  return data.results;
}
