import { ChatInput } from './ChatInput';
import { MessageList } from './MessageList';
import { SuggestedQuestions } from './SuggestedQuestions';
import './ChatArea.less';

export function ChatArea() {
  return (
    <div className="chat-area">
      <MessageList />
      <SuggestedQuestions />
      <ChatInput />
    </div>
  );
}
