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
        <Empty description="向系统提问，获取基于个人资料的精准回答" />
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