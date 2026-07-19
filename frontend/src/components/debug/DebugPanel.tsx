import { BugOutlined } from '@ant-design/icons';
import { Divider, InputNumber, Typography } from 'antd';
import { useAppContext } from '../../context/AppContext';
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector';
import { SimilarityThresholdSlider } from './SimilarityThresholdSlider';
import './DebugPanel.less';

const { Title, Text } = Typography;

export function DebugPanel() {
  const { debug, setDebug } = useAppContext();

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <BugOutlined className="debug-icon" />
        <Title level={5} className="debug-title">
          ????
        </Title>
      </div>
      <Text type="secondary" className="debug-desc">
        ???????????????
      </Text>

      <Divider className="debug-divider" />

      <KnowledgeBaseSelector />
      <SimilarityThresholdSlider />

      <div className="topk-setting">
        <label className="debug-label">?? Top-K</label>
        <InputNumber
          min={1}
          max={20}
          value={debug.topK}
          onChange={(value) => setDebug({ topK: value ?? 10 })}
          className="topk-input"
        />
      </div>
    </div>
  );
}
