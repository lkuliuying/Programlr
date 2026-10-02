import { afterEach, expect, test } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ToolchainProbe } from './ToolchainProbe';

afterEach(cleanup);

test('React 与 Ant Design 能渲染并处理事件', () => {
  render(<ToolchainProbe />);
  fireEvent.click(screen.getByRole('button', { name: '检查组件' }));
  expect(screen.getByRole('button', { name: '工具检查完成' }).textContent).toBe(
    '工具检查完成',
  );
});

test('重新挂载时不会保留上次验证状态', () => {
  const view = render(<ToolchainProbe />);
  fireEvent.click(screen.getByRole('button', { name: '检查组件' }));
  view.unmount();
  render(<ToolchainProbe />);
  expect(screen.getByRole('button', { name: '检查组件' })).toBeTruthy();
});
