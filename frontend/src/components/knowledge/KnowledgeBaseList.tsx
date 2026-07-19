import { FileTextOutlined } from '@ant-design/icons';
import { Empty, List, Spin, Tag, Typography } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './KnowledgeBaseList.less';

const { Text } = Typography;

export function KnowledgeBaseList() {
  const { files, filesLoading } = useAppContext();

  if (filesLoading) {
    return (
      <div className="kb-loading">
        <Spin size="small" />
      </div>
    );
  }

  if (files.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无文档" />;
  }

  return (
    <List
      className="kb-list"
      size="small"
      dataSource={files}
      renderItem={(file) => (
        <List.Item className="kb-item">
          <List.Item.Meta
            avatar={<FileTextOutlined className="kb-icon" />}
            title={
              <Text ellipsis className="kb-name">
                {file.original_name}
              </Text>
            }
            description={
              <span className="kb-meta">
                {file.total_chunks} �?· {file.upload_time}
              </span>
            }
          />
          <Tag color={file.status === 'success' ? 'success' : 'default'}>{file.status}</Tag>
        </List.Item>
      )}
    />
  );
}
