import { DebugPanel } from '../debug/DebugPanel';
import './RightSidebar.less';

export function RightSidebar() {
  return (
    <aside className="right-sidebar">
      <DebugPanel />
    </aside>
  );
}
