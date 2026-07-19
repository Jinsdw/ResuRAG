import { Select } from 'antd';
import { useAppContext } from '../../context/AppContext';
import './KnowledgeBaseSelector.less';

export function KnowledgeBaseSelector() {
  const { files, debug, setDebug } = useAppContext();

  const options = [
    { value: '', label: '?????' },
    ...files.map((file) => ({
      value: file.file_uuid,
      label: file.original_name,
    })),
  ];

  return (
    <div className="kb-selector">
      <label className="debug-label">?????</label>
      <Select
        value={debug.selectedFileUuid ?? ''}
        options={options}
        onChange={(value) => setDebug({ selectedFileUuid: value || null })}
        placeholder="?????"
        className="kb-select"
      />
    </div>
  );
}
