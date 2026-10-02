import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { AppErrorBoundary } from './AppErrorBoundary';

afterEach(cleanup);

test('正常渲染保留工作区内容', () => {
  render(
    <AppErrorBoundary>
      <p>源码工作区</p>
    </AppErrorBoundary>,
  );
  expect(screen.getByText('源码工作区')).toBeTruthy();
  expect(screen.queryByRole('alert')).toBeNull();
});

test('渲染失败显示恢复入口，不展示原始错误或自动重新提交', () => {
  const reload = vi.fn();
  const secretMessage = 'synthetic-private-content';
  function Broken(): never {
    throw new Error(secretMessage);
  }
  render(
    <AppErrorBoundary onReload={reload}>
      <Broken />
    </AppErrorBoundary>,
    { onCaughtError: vi.fn() },
  );
  expect(screen.getByRole('alert').textContent).toContain('避免重复提交');
  expect(screen.queryByText(secretMessage)).toBeNull();
  expect(reload).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '重新加载当前工作区' }));
  expect(reload).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole('link', { name: '查看系统与任务' }).getAttribute('href'),
  ).toBe('?view=jobs');
});
