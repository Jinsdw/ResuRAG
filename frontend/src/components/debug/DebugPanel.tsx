import { BugOutlined } from '@ant-design/icons';
import { Divider, InputNumber, Typography } from 'antd';
import { useMemo } from 'react';
import { useAppContext } from '../../context/AppContext';
import type { ChatMessage, Citation } from '../../types';
import { CitationList } from './CitationList';
import { SimilarityThresholdSlider } from './SimilarityThresholdSlider';
import './DebugPanel.less';

const { Title, Text } = Typography;

function getLatestCitationState(messages: ChatMessage[]): {
  citations: Citation[];
  loading: boolean;
} {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i];
    if (msg.role === 'assistant') {
      return {
        citations: msg.citations ?? [],
        loading: msg.citations === undefined,
      };
    }
  }
  return { citations: [], loading: false };
}

export function DebugPanel() {
  const { debug, setDebug, activeSession } = useAppContext();

  const { citations, loading: citationsLoading } = useMemo(
    () => getLatestCitationState(activeSession?.messages ?? []),
    [activeSession?.messages],
  );

  return (
    <div className="debug-panel">
      <div className="debug-panel__controls">
        <div className="debug-header">
          <BugOutlined className="debug-icon" />
          <Title level={5} className="debug-title">
            调试面板
          </Title>
        </div>
        <Text type="secondary" className="debug-desc">
          调整检索参数，优化个人信息问答的匹配质量
        </Text>

        <Divider className="debug-divider" />

        <SimilarityThresholdSlider />

        <div className="topk-setting">
          <label className="debug-label">检索 Top-K</label>
          <InputNumber
            min={1}
            max={10}
            value={debug.topK}
            onChange={(value) => setDebug({ topK: value ?? 5 })}
            className="topk-input"
          />
        </div>
      </div>

      <div className="debug-panel__citations">
        <CitationList citations={citations} loading={citationsLoading} />
      </div>
    </div>
  );
}
