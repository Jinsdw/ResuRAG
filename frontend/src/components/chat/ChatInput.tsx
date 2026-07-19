import { SendOutlined } from '@ant-design/icons';
import { Button, Input } from 'antd';
import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import './ChatInput.less';

export function ChatInput() {
  const { sendMessage, sending } = useAppContext();
  const [value, setValue] = useState('');

  const handleSend = async () => {
    if (!value.trim()) return;
    const query = value;
    setValue('');
    await sendMessage(query);
  };

  return (
    <div className="chat-input">
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="??????..."
        autoSize={{ minRows: 2, maxRows: 4 }}
        disabled={sending}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            void handleSend();
          }
        }}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        loading={sending}
        className="chat-send-btn"
        onClick={() => void handleSend()}
      >
        ??
      </Button>
    </div>
  );
}
