import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import './ChatArea.less';

export function ChatArea() {
  return (
    <div className="chat-area">
      <MessageList />
      <ChatInput />
    </div>
  );
}
