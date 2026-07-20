import { FINGERPRINT_HEADER, getBrowserFingerprint } from '../utils/fingerprint';

const DOC_BASE = '/api/doc';
const INDEXING_BASE = '/api/indexing';
const RETRIEVAL_BASE = '/api/retrieval';
const GENERATION_BASE = '/api/generation';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (url.startsWith(GENERATION_BASE)) {
    headers.set(FINGERPRINT_HEADER, getBrowserFingerprint());
  }
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export { DOC_BASE, FINGERPRINT_HEADER, INDEXING_BASE, RETRIEVAL_BASE, GENERATION_BASE, request };
