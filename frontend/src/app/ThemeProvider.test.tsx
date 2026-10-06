import { readFileSync } from 'node:fs';
import { useState } from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { theme } from 'antd';
import { ThemeProvider } from './ThemeProvider';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});
function Probe() {
  const { token } = theme.useToken();
  return <output aria-label="主题">{JSON.stringify(token)}</output>;
}
test.each([null, 'dark', 'light', 'invalid'])(
  '历史偏好 %s 不改变浅色主题',
  (saved) => {
    if (saved) localStorage.setItem('learning-lab.ui-theme', saved);
    const read = vi.spyOn(Storage.prototype, 'getItem');
    const write = vi.spyOn(Storage.prototype, 'setItem');
    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>,
    );
    const token = JSON.parse(screen.getByLabelText('主题').textContent!);
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.documentElement.style.colorScheme).toBe('light');
    expect(token.colorBgContainer).toBe('#ffffff');
    expect(token.colorText).toBe('#142650');
    expect(read).not.toHaveBeenCalled();
    expect(write).not.toHaveBeenCalled();
  },
);
test('首屏不依赖主题脚本，存储不可用时仍保持草稿', () => {
  const html = readFileSync('index.html', 'utf8');
  expect(html).toContain('data-theme="light"');
  expect(html).not.toContain('theme-init.js');
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('不可读取');
  });
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('不可写入');
  });
  function Draft() {
    const [value, setValue] = useState('');
    return (
      <input
        aria-label="草稿"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
    );
  }
  const view = render(
    <ThemeProvider>
      <Draft />
    </ThemeProvider>,
  );
  const input = screen.getByLabelText('草稿');
  fireEvent.change(input, { target: { value: '保留输入' } });
  view.rerender(
    <ThemeProvider>
      <Draft />
    </ThemeProvider>,
  );
  expect(screen.getByLabelText('草稿')).toBe(input);
  expect(input).toHaveProperty('value', '保留输入');
});

test('系统偏好深色时仍使用浅色控件与根配色', () => {
  const matchMedia = window.matchMedia.bind(window);
  vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
    ...matchMedia(query),
    matches: query === '(prefers-color-scheme: dark)',
  }));
  render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  expect(window.matchMedia('(prefers-color-scheme: dark)').matches).toBe(true);
  expect(document.documentElement.style.colorScheme).toBe('light');
  expect(
    JSON.parse(screen.getByLabelText('主题').textContent!).colorBgContainer,
  ).toBe('#ffffff');
});
test('浅色主按钮的三个交互状态与白字对比度满足 AA', () => {
  render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  const token = JSON.parse(screen.getByLabelText('主题').textContent!);
  const luminance = (hex: string) => {
    const channels = [1, 3, 5].map((offset) => {
      const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
      return value <= 0.04045
        ? value / 12.92
        : ((value + 0.055) / 1.055) ** 2.4;
    });
    return (
      channels[0]! * 0.2126 + channels[1]! * 0.7152 + channels[2]! * 0.0722
    );
  };
  const foreground = luminance(token.colorTextLightSolid);
  for (const background of [
    token.colorPrimary,
    token.colorPrimaryHover,
    token.colorPrimaryActive,
  ]) {
    const value = luminance(background);
    expect(
      (Math.max(foreground, value) + 0.05) /
        (Math.min(foreground, value) + 0.05),
    ).toBeGreaterThanOrEqual(4.5);
  }
});
