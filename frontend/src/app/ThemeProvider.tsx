import { createContext, useContext, useLayoutEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ConfigProvider, theme } from 'antd';

export type ThemeMode = 'dark' | 'light';
export const themeStorageKey = 'learning-lab.ui-theme';
export function readTheme(): ThemeMode {
  try {
    const value = localStorage.getItem(themeStorageKey);
    return value === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}
const ThemeContext = createContext({
  mode: 'dark' as ThemeMode,
  setMode: (mode: ThemeMode) => {
    void mode;
  },
});
export const useTheme = () => useContext(ThemeContext);
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, updateMode] = useState<ThemeMode>(readTheme);
  const dark = mode === 'dark';
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = mode;
    document.documentElement.style.colorScheme = mode;
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', dark ? '#07141e' : '#f3f6f9');
  }, [mode, dark]);
  function setMode(value: ThemeMode) {
    updateMode(value);
    try {
      localStorage.setItem(themeStorageKey, value);
    } catch {
      // 偏好写入失败不阻止切换，也不影响任何业务操作。
    }
  }
  return (
    <ThemeContext.Provider value={{ mode, setMode }}>
      <ConfigProvider
        theme={{
          algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: dark ? '#16d6af' : '#007f6a',
            colorBgBase: dark ? '#07141e' : '#f3f6f9',
            colorBgContainer: dark ? '#0d202d' : '#ffffff',
            colorBgElevated: dark ? '#122a39' : '#ffffff',
            colorText: dark ? '#e1edf5' : '#203340',
            colorTextSecondary: dark ? '#a4bdcd' : '#516c7d',
            colorBorder: dark ? '#244656' : '#d5e0e7',
            borderRadius: 5,
            fontSize: 13,
            fontFamily:
              '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif',
          },
        }}
      >
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}
