import { BulbOutlined, CommentOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import { Spin, Typography } from 'antd';
import type { ChatMessage } from '../../types';
import './MessageBubble.less';

const { Paragraph, Text } = Typography;

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-row message-row--user">
        <div className="message-avatar message-avatar--user">
          <UserOutlined />
        </div>
        <div className="message-bubble message-bubble--user">
          <Paragraph className="message-content">{message.content}</Paragraph>
        </div>
      </div>
    );
  }

  const reasoningText = message.reasoning?.trim() ?? '';
  const answerText = message.content?.trim() ?? '';
  const hasReasoning = reasoningText.length > 0;
  const hasAnswer = answerText.length > 0;
  const waitingForStream =
    message.isStreaming && !hasReasoning && !hasAnswer;

  return (
    <div className="message-row message-row--assistant">
      <div className="message-avatar message-avatar--assistant">
        <RobotOutlined />
      </div>
      <div className="message-bubble message-bubble--assistant">
        {waitingForStream ? (
          <Spin size="small" />
        ) : (
          <>
            {hasReasoning && (
              <div className="message-block message-block--reasoning">
                <div className="message-block__label">
                  <BulbOutlined className="message-block__icon" />
                  <Text className="message-block__title">思考过程</Text>
                </div>
                <Paragraph className="message-reasoning">{reasoningText}</Paragraph>
              </div>
            )}
            {hasAnswer ? (
              <div
                className={`message-block message-block--answer${hasReasoning ? ' message-block--answer-separated' : ''}`}
              >
                <div className="message-block__label">
                  <CommentOutlined className="message-block__icon" />
                  <Text className="message-block__title">回答</Text>
                </div>
                <Paragraph className="message-content">{message.content}</Paragraph>
              </div>
            ) : (
              message.isStreaming && (
                <div className="message-block message-block--answer-pending">
                  <Spin size="small" />
                  <Text type="secondary" className="message-block__pending-text">
                    正在生成回答…
                  </Text>
                </div>
              )
            )}
          </>
        )}
      </div>
    </div>
  );
}
