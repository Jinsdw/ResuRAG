import { useCallback, useEffect, useState } from 'react';
import type { KnowledgeFile } from '../types';
import { listFiles, uploadDocument } from '../services/docService';
import { indexDocument } from '../services/indexingService';

export function useKnowledgeBase() {
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listFiles();
      setFiles(data);
    } catch {
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const upload = useCallback(
    async (file: File) => {
      setUploading(true);
      try {
        const result = await uploadDocument(file);
        await indexDocument(result.file_uuid, result.chunk_dir);
        await refresh();
        return result;
      } finally {
        setUploading(false);
      }
    },
    [refresh],
  );

  return { files, loading, uploading, refresh, upload };
}
