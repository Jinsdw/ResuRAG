import { PlusOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './NewSessionButton.less';

export function NewSessionButton() {
  const { createNewSession } = useAppContext();

  return (
    <Button
      type="primary"
      icon={<PlusOutlined />}
      block
      className="new-session-btn"
      onClick={createNewSession}
    >
      新建会话
    </Button>
  );
}
