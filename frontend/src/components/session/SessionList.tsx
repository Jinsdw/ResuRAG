import { DeleteOutlined, MessageOutlined } from '@ant-design/icons';
import { Empty, List, Popconfirm, Typography } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './SessionList.less';

const { Text } = Typography;

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function SessionList() {
  const { sessions, activeSessionId, selectSession, deleteSession } = useAppContext();

  if (sessions.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无会话" />;
  }

  return (
    <List
      className="session-list"
      dataSource={sessions}
      renderItem={(session) => {
        const active = session.id === activeSessionId;
        return (
          <List.Item
            className={`session-item ${active ? 'session-item--active' : ''}`}
            onClick={() => selectSession(session.id)}
            actions={[
              <Popconfirm
                key="delete"
                title="确定删除此会话？"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  deleteSession(session.id);
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <DeleteOutlined
                  className="session-delete"
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              avatar={<MessageOutlined className="session-icon" />}
              title={
                <Text ellipsis className="session-title">
                  {session.title}
                </Text>
              }
              description={formatTime(session.updatedAt)}
            />
          </List.Item>
        );
      }}
    />
  );
}
