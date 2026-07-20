import { useCallback, useLayoutEffect, useMemo, useRef } from 'react';
import type { ChatMessage } from '../types';

const BOTTOM_THRESHOLD_PX = 80;

function isNearBottom(element: HTMLElement): boolean {
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight;
  return distance <= BOTTOM_THRESHOLD_PX;
}

function scrollContainerToBottom(element: HTMLElement) {
  element.scrollTop = element.scrollHeight;
}

/** 流式更新时仅在用户处于底部附近时自动滚到底；用户上滑阅读时不打断 */
export function useStickToBottomScroll(
  sessionId: string | null | undefined,
  messages: ChatMessage[],
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const prevMessageCountRef = useRef(0);

  const scrollAnchor = useMemo(() => {
    if (messages.length === 0) return `${sessionId ?? ''}:empty`;
    const last = messages[messages.length - 1];
    return [
      sessionId ?? '',
      messages.length,
      last.id,
      last.content.length,
      (last.reasoning ?? '').length,
      last.isStreaming ? '1' : '0',
    ].join('|');
  }, [sessionId, messages]);

  const onScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    stickToBottomRef.current = isNearBottom(el);
  }, []);

  useLayoutEffect(() => {
    stickToBottomRef.current = true;
    prevMessageCountRef.current = 0;
    const el = containerRef.current;
    if (el) scrollContainerToBottom(el);
  }, [sessionId]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (messages.length > prevMessageCountRef.current) {
      const added = messages.slice(prevMessageCountRef.current);
      if (added.some((msg) => msg.role === 'user')) {
        stickToBottomRef.current = true;
      }
    }
    prevMessageCountRef.current = messages.length;

    if (stickToBottomRef.current) {
      scrollContainerToBottom(el);
    }
  }, [scrollAnchor, messages.length]);

  return { containerRef, onScroll };
}
