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
          colorText: colors.primary,
          colorTextSecondary: colors.textSecondary,
          colorBorder: colors.border,
          colorBgContainer: colors.bg,
          colorBgLayout: colors.bgSecondary,
          colorBgElevated: colors.bg,
          borderRadius: 10,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        },
        components: {
          Button: {
            primaryShadow: '0 2px 6px rgba(99, 102, 241, 0.25)',
          },
          Input: {
            activeBorderColor: colors.accent,
            hoverBorderColor: colors.accentLight,
          },
          Slider: {
            trackBg: colors.border,
            trackHoverBg: colors.textMuted,
            handleColor: colors.accent,
            handleActiveColor: colors.accentHover,
          },
        },
      }}
    >
      <AppProvider>
        <HomePage />
      </AppProvider>
    </ConfigProvider>
  );
}
