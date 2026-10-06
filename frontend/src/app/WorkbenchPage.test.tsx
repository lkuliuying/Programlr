import { afterEach, expect, test } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { WorkbenchPage } from './WorkspaceModulePages';
afterEach(cleanup);
test('新版首页保留无障碍标题和单实例内容，隐藏切换保留草稿', () => {
  const content = (
    <label>
      首页测试草稿
      <input defaultValue="" />
    </label>
  );
  const view = render(<WorkbenchPage active>{content}</WorkbenchPage>);
  expect(
    screen.getByRole('heading', { name: '工作台' }).closest('header')
      ?.className,
  ).toContain('sr-only');
  const input = screen.getByRole('textbox');
  fireEvent.change(input, { target: { value: '保留未提交内容' } });
  view.rerender(<WorkbenchPage active={false}>{content}</WorkbenchPage>);
  view.rerender(<WorkbenchPage active>{content}</WorkbenchPage>);
  expect(screen.getByRole('textbox')).toBe(input);
  expect(input).toHaveProperty('value', '保留未提交内容');
  expect(
    screen.queryByRole('navigation', { name: '工作台内容分页' }),
  ).toBeNull();
  expect(screen.getByRole('region', { name: /^工作台$/ }).contains(input)).toBe(
    true,
  );
});
