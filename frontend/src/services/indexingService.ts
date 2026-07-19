import { INDEXING_BASE, request } from './api';

interface IndexResponse {
  code: number;
  message: string;
  data: {
    file_uuid: string;
    total_chunks: number;
    indexed_count: number;
  };
}

export async function indexDocument(
  fileUuid: string,
  chunkDir: string,
  tenantId = 'default',
): Promise<IndexResponse['data']> {
  const data = await request<IndexResponse>(`${INDEXING_BASE}/api/v1/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_uuid: fileUuid,
      tenant_id: tenantId,
      chunk_dir: chunkDir,
    }),
  });
  return data.data;
}
