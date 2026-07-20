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
  similarityThreshold?: number;
}): Promise<SearchResult[]> {
  const data = await request<SearchResponse>(`${RETRIEVAL_BASE}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: params.query,
      top_k: params.topK ?? 10,
      similarity_threshold: params.similarityThreshold ?? 0,
    }),
  });
  return data.results;
}
