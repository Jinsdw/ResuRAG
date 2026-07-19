import { Layout, Typography } from 'antd';
import { CenterPanel } from './CenterPanel';
import { LeftSidebar } from './LeftSidebar';
import { RightSidebar } from './RightSidebar';
import './MainLayout.less';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

export function MainLayout() {
  return (
    <Layout className="main-layout">
      <Header className="main-header">
        <Title level={4} className="main-logo">
          ResuRAG
        </Title>
        <span className="main-subtitle">???? RAG ????</span>
      </Header>
      <Layout className="main-body">
        <Sider width={280} className="main-sider main-sider--left">
          <LeftSidebar />
        </Sider>
        <Content className="main-content">
          <CenterPanel />
        </Content>
        <Sider width={280} className="main-sider main-sider--right">
          <RightSidebar />
        </Sider>
      </Layout>
    </Layout>
  );
}
