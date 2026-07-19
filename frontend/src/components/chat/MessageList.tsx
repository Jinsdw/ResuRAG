import { Empty } from 'antd';
import { useAppContext } from '../../context/AppContext';
import { MessageBubble } from './MessageBubble';
import './MessageList.less';

export function MessageList() {
  const { activeSession } = useAppContext();
  const messages = activeSession?.messages ?? [];

  if (messages.length === 0) {
    return (
      <div className="message-empty">
        <Empty description="??????????????" />
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
