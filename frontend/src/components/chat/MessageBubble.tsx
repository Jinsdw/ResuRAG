import { RobotOutlined, UserOutlined } from '@ant-design/icons';
import { Spin, Typography } from 'antd';
import type { ChatMessage } from '../../types';
import './MessageBubble.less';

const { Paragraph } = Typography;

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--assistant'}`}>
      <div className={`message-avatar ${isUser ? 'message-avatar--user' : 'message-avatar--assistant'}`}>
        {isUser ? <UserOutlined /> : <RobotOutlined />}
      </div>
      <div className={`message-bubble ${isUser ? 'message-bubble--user' : 'message-bubble--assistant'}`}>
        {message.isStreaming && !message.content ? (
          <Spin size="small" />
        ) : (
          <Paragraph className="message-content">{message.content}</Paragraph>
        )}
      </div>
    </div>
  );
}
