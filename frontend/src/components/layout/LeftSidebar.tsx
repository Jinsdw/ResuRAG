import { Divider, Typography } from 'antd';
import { DocumentUpload } from '../knowledge/DocumentUpload';
import { KnowledgeBaseList } from '../knowledge/KnowledgeBaseList';
import { NewSessionButton } from '../session/NewSessionButton';
import { SessionList } from '../session/SessionList';
import './LeftSidebar.less';

const { Title } = Typography;

export function LeftSidebar() {
  return (
    <aside className="left-sidebar">
      <div className="sidebar-section sidebar-section--sessions">
        <Title level={5} className="sidebar-title">
          ????
        </Title>
        <NewSessionButton />
        <SessionList />
      </div>

      <Divider className="sidebar-divider" />

      <div className="sidebar-section sidebar-section--knowledge">
        <Title level={5} className="sidebar-title">
          ???
        </Title>
        <DocumentUpload />
        <KnowledgeBaseList />
      </div>
    </aside>
  );
}
