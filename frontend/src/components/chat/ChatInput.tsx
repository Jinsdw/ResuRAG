import { ArrowUpOutlined, LoadingOutlined } from '@ant-design/icons';
import { Input } from 'antd';
import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';
import './ChatInput.less';

export function ChatInput() {
  const { sendMessage, sending } = useAppContext();
  const [value, setValue] = useState('');

  const canSend = value.trim().length > 0 && !sending;

  const handleSend = async () => {
    if (!canSend) return;
    const query = value;
    setValue('');
    await sendMessage(query);
  };

  return (
    <div className="chat-input">
      <div className="chat-input-box">
        <Input.TextArea
          className="chat-input-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="请输入关于个人信息的问题，例如：你的工作经历是什么？"
          autoSize={{ minRows: 2, maxRows: 4 }}
          disabled={sending}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <button
          type="button"
          className={`chat-send-btn ${canSend ? 'chat-send-btn--active' : ''}`}
          disabled={!canSend}
          aria-label="发送"
          onClick={() => void handleSend()}
        >
          {sending ? <LoadingOutlined spin /> : <ArrowUpOutlined />}
        </button>
      </div>
    </div>
  );
}