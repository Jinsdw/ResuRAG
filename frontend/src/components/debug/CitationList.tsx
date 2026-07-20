import { Spin, Tag, Tooltip, Typography } from 'antd';
import type { Citation } from '../../types';
import { scoreColor, scoreLabel } from '../../styles/theme';
import './CitationList.less';

const { Text } = Typography;

interface CitationListProps {
  citations: Citation[];
  loading?: boolean;
}

export function CitationList({ citations, loading = false }: CitationListProps) {
  if (loading) {
    return (
      <div className="citation-list">
        <Text className="citation-title">引用来源</Text>
        <div className="citation-list__loading">
          <Spin size="small" />
          <Text type="secondary">检索中…</Text>
        </div>
      </div>
    );
  }

  if (!citations.length) {
    return (
      <div className="citation-list citation-list--empty">
        <Text className="citation-title">引用来源</Text>
        <Text type="secondary" className="citation-empty">
          发送问题后，检索到的文档片段将显示在这里
        </Text>
      </div>
    );
  }

  return (
    <div className="citation-list">
      <Text className="citation-title">引用来源</Text>
      {citations.map((item) => (
        <div key={item.chunk_id} className="citation-item">
          <div className="citation-header">
            <Tag color="blue">[{item.index}]</Tag>
            <Text strong className="citation-source">
              {item.source_file_name}
              {item.source_page ? ` · 第 ${item.source_page} 页` : ''}
            </Text>
            <Tag
              style={{
                color: scoreColor(item.score),
                borderColor: scoreColor(item.score),
                background: `${scoreColor(item.score)}14`,
              }}
            >
              {scoreLabel(item.score)} · {(item.score * 100).toFixed(0)}%
            </Tag>
          </div>
          <Tooltip
            title={item.content}
            placement="left"
            overlayClassName="citation-content-tooltip"
          >
            <div className="citation-content">{item.content}</div>
          </Tooltip>
        </div>
      ))}
    </div>
  );
}
