import type { SearchResult, StreamEvent } from '../types';
import { GENERATION_BASE } from './api';

function parseSseLine(line: string): StreamEvent | null {
  if (!line.startsWith('data: ')) return null;
  try {
    return JSON.parse(line.slice(6)) as StreamEvent;
  } catch {
    return null;
  }
}

export async function* streamGenerate(
  query: string,
  chunks: SearchResult[],
  sessionId: string,
): AsyncGenerator<StreamEvent> {
  const response = await fetch(`${GENERATION_BASE}/api/v1/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, query, chunks }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || '生成失败');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('无法读取响应流');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const event = parseSseLine(trimmed);
      if (event) yield event;
    }
  }
}
