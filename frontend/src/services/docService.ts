import type { KnowledgeFile, UploadResult } from '../types';
import { DOC_BASE, request } from './api';

interface FilesResponse {
  files: KnowledgeFile[];
}

interface UploadResponse {
  status: string;
  data: UploadResult;
}

export async function listFiles(tenantId = 'default'): Promise<KnowledgeFile[]> {
  const data = await request<FilesResponse>(`${DOC_BASE}/files?tenant_id=${tenantId}`);
  return data.files;
}

export async function uploadDocument(file: File, tenantId = 'default'): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${DOC_BASE}/upload?tenant_id=${tenantId}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || '上传失败');
  }

  const data = (await response.json()) as UploadResponse;
  return data.data;
}
