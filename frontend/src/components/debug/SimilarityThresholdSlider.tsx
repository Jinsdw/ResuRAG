import { Slider, Typography } from 'antd';
import { useAppContext } from '../../context/AppContext';
import { colors } from '../../styles/theme';
import './SimilarityThresholdSlider.less';

const { Text } = Typography;

export function SimilarityThresholdSlider() {
  const { debug, setDebug } = useAppContext();

  return (
    <div className="threshold-slider">
      <div className="threshold-header">
        <label className="debug-label">相似度阈值 (0–1)</label>
        <Text className="threshold-value">{debug.similarityThreshold.toFixed(2)}</Text>
      </div>
      <div className="threshold-slider-track">
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={debug.similarityThreshold}
          onChange={(value) => setDebug({ similarityThreshold: value })}
          tooltip={{ formatter: (v) => (v ?? 0).toFixed(2) }}
        />
      </div>
      <div className="threshold-legend">
        <span style={{ color: colors.success }}>● 高相关 ≥0.70</span>
        <span style={{ color: colors.warning }}>● 中相关 0.40–0.70</span>
        <span style={{ color: colors.danger }}>● 低相关 &lt;0.40</span>
      </div>
    </div>
  );
}