const DOC_BASE = '/api/doc';
const INDEXING_BASE = '/api/indexing';
const RETRIEVAL_BASE = '/api/retrieval';
const GENERATION_BASE = '/api/generation';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export { DOC_BASE, INDEXING_BASE, RETRIEVAL_BASE, GENERATION_BASE, request };
