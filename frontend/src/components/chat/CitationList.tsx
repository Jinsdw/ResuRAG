import { Tag, Typography } from 'antd';
import type { Citation } from '../../types';
import { scoreColor, scoreLabel } from '../../styles/theme';
import './CitationList.less';

const { Text, Paragraph } = Typography;

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (!citations.length) return null;

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
          <Paragraph ellipsis={{ rows: 2 }} className="citation-content">
            {item.content}
          </Paragraph>
        </div>
      ))}
    </div>
  );
}