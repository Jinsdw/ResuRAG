import { NewSessionButton } from '../session/NewSessionButton';
import { SessionList } from '../session/SessionList';
import './LeftSidebar.less';

export function LeftSidebar() {
  return (
    <aside className="left-sidebar">
      <div className="sidebar-section sidebar-section--sessions">
        <NewSessionButton />
        <SessionList />
      </div>
    </aside>
  );
}