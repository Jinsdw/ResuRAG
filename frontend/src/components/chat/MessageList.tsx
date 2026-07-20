import { Empty } from 'antd';
import { useAppContext } from '../../context/AppContext';
import { useStickToBottomScroll } from '../../hooks/useStickToBottomScroll';
import { MessageBubble } from './MessageBubble';
import './MessageList.less';

export function MessageList() {
  const { activeSession } = useAppContext();
  const messages = activeSession?.messages ?? [];
  const { containerRef, onScroll } = useStickToBottomScroll(activeSession?.id, messages);

  return (
    <div ref={containerRef} className="message-list" onScroll={onScroll}>
      {messages.length === 0 ? (
        <div className="message-empty">
          <Empty description="向系统提问，获取基于个人资料的精准回答" />
        </div>
      ) : (
        messages.map((message) => <MessageBubble key={message.id} message={message} />)
      )}
    </div>
  );
}
