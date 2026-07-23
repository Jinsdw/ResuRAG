import { BulbOutlined } from '@ant-design/icons';
import { Spin, Typography } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './SuggestedQuestions.less';

const { Text } = Typography;

export function SuggestedQuestions() {
  const { suggestions, suggestionsLoading, sending, sendMessage } = useAppContext();

  if (sending || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="suggested-questions">
      <div className="suggested-questions__header">
        <BulbOutlined className="suggested-questions__icon" />
        <Text type="secondary" className="suggested-questions__title">
          猜你想问
        </Text>
        {suggestionsLoading && <Spin size="small" />}
      </div>
      <div className="suggested-questions__list">
        {suggestions.map((question, index) => (
          <button
            key={`${index}-${question}`}
            type="button"
            className="suggested-questions__chip"
            disabled={suggestionsLoading}
            onClick={() => void sendMessage(question)}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
