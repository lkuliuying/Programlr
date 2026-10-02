import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { useState } from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import {
  readTheme,
  ThemeProvider,
  themeStorageKey,
  useTheme,
} from './ThemeProvider';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});
test('主题仅接受合法偏好，无记录、非法值和不可读取时默认深色', () => {
  expect(readTheme()).toBe('dark');
  localStorage.setItem(themeStorageKey, 'light');
  expect(readTheme()).toBe('light');
  localStorage.setItem(themeStorageKey, 'dark');
  expect(readTheme()).toBe('dark');
  localStorage.setItem(themeStorageKey, 'invalid');
  expect(readTheme()).toBe('dark');
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new DOMException('不可用');
  });
  expect(readTheme()).toBe('dark');
});
test('外部首屏脚本在存储失败时安全回落，和 Provider 采用相同偏好规则', () => {
  const source = readFileSync('public/theme-init.js', 'utf8');
  for (const value of [null, 'light', 'dark', 'invalid', 'blocked']) {
    const root = {
      dataset: {} as Record<string, string>,
      style: {} as Record<string, string>,
    };
    runInNewContext(source, {
      document: { documentElement: root },
      localStorage: {
        getItem: () => {
          if (value === 'blocked') throw new Error('不可用');
          return value;
        },
      },
    });
    expect(root.dataset.theme).toBe(value === 'light' ? 'light' : 'dark');
    expect(root.style.colorScheme).toBe(root.dataset.theme);
  }
});
test('切换主题及写入失败不重建表单、不提交操作，并可恢复偏好', () => {
  const submit = vi.fn();
  function Draft() {
    const { mode, setMode } = useTheme();
    const [answer, setAnswer] = useState('');
    return (
      <>
        <button onClick={() => setMode(mode === 'dark' ? 'light' : 'dark')}>
          切换主题
        </button>
        <form onSubmit={submit}>
          <label>
            未提交答案
            <input
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
            />
          </label>
          <button type="submit">提交</button>
        </form>
      </>
    );
  }
  const view = render(
    <ThemeProvider>
      <Draft />
    </ThemeProvider>,
  );
  fireEvent.change(screen.getByLabelText('未提交答案'), {
    target: { value: '保留输入' },
  });
  fireEvent.click(screen.getByText('切换主题'));
  expect(document.documentElement.dataset.theme).toBe('light');
  expect(localStorage.getItem(themeStorageKey)).toBe('light');
  expect((screen.getByLabelText('未提交答案') as HTMLInputElement).value).toBe(
    '保留输入',
  );
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new DOMException('不可用');
  });
  fireEvent.click(screen.getByText('切换主题'));
  expect(document.documentElement.dataset.theme).toBe('dark');
  expect((screen.getByLabelText('未提交答案') as HTMLInputElement).value).toBe(
    '保留输入',
  );
  expect(submit).not.toHaveBeenCalled();
  view.unmount();
  render(
    <ThemeProvider>
      <Draft />
    </ThemeProvider>,
  );
  expect(document.documentElement.dataset.theme).toBe('light');
});
