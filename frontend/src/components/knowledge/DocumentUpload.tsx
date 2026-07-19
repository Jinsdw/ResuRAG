import { InboxOutlined } from '@ant-design/icons';
import { message, Upload, type UploadProps } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './DocumentUpload.less';

const { Dragger } = Upload;

export function DocumentUpload() {
  const { uploadFile, uploading } = useAppContext();

  const props: UploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    accept: '.pdf,.docx,.txt,.md',
    disabled: uploading,
    beforeUpload: (file) => {
      void (async () => {
        try {
          const result = await uploadFile(file);
          message.success(`${result.original_name} ???????`);
        } catch (error) {
          const msg = error instanceof Error ? error.message : '????';
          message.error(msg);
        }
      })();
      return false;
    },
  };

  return (
    <Dragger {...props} className="doc-upload">
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">?????????</p>
      <p className="ant-upload-hint">?? PDF?DOCX?TXT?MD</p>
    </Dragger>
  );
}
