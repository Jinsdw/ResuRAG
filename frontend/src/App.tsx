import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AppProvider } from './context/AppContext';
import { HomePage } from './pages/HomePage';
import { colors } from './styles/theme';
import './styles/global.less';

export function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: colors.accent,
          colorSuccess: colors.success,
          colorWarning: colors.warning,
          colorError: colors.danger,
          colorBgContainer: colors.bg,
          colorBgLayout: colors.bgSecondary,
          borderRadius: 8,
        },
      }}
    >
      <AppProvider>
        <HomePage />
      </AppProvider>
    </ConfigProvider>
  );
}
