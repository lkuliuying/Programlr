import { useLayoutEffect } from 'react';
import type { ReactNode } from 'react';
import { ConfigProvider, theme } from 'antd';

export function ThemeProvider({ children }: { children: ReactNode }) {
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = 'light';
    document.documentElement.style.colorScheme = 'light';
  }, []);
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1767d8',
          colorPrimaryHover: '#1b6bd5',
          colorPrimaryActive: '#1359bb',
          colorTextLightSolid: '#ffffff',
          colorBgBase: '#f4f8fe',
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorText: '#142650',
          colorTextSecondary: '#5d7095',
          colorBorder: '#dce7f6',
          borderRadius: 8,
          fontSize: 14,
          fontFamily: '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif',
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
}
