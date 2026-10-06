import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { useState } from 'react';
import { WorkspaceShell } from './WorkspaceShell';
import type { WorkspaceSection } from './workspace-location';

beforeEach(() => {
  vi.stubGlobal('innerWidth', 390);
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute('open');
      this.dispatchEvent(new Event('close'));
    },
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
function setup() {
  const navigate = vi.fn();
  render(
    <WorkspaceShell section="api" onSection={navigate}>
      <label>
        未提交笔记
        <input defaultValue="保留这段文字" />
      </label>
    </WorkspaceShell>,
  );
  const trigger = screen.getByRole('button', { name: '功能导航' });
  fireEvent.click(trigger);
  return {
    navigate,
    trigger,
    dialog: screen.getByRole('dialog', { name: '功能导航菜单' }),
  };
}
test('窄屏三入口菜单聚焦当前工作区，导航恢复焦点和草稿', () => {
  const { navigate, trigger, dialog } = setup();
  expect(document.activeElement).toBe(
    within(dialog).getByRole('button', { name: '项目工作区' }),
  );
  expect(within(dialog).getAllByRole('navigation')).toHaveLength(3);
  expect(within(dialog).getAllByRole('button')).toHaveLength(4);
  fireEvent.click(within(dialog).getByRole('button', { name: '项目管理' }));
  expect(navigate).toHaveBeenCalledExactlyOnceWith('import');
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(screen.getByLabelText('未提交笔记')).toHaveProperty(
    'value',
    '保留这段文字',
  );
});
test.each(['cancel', 'backdrop', 'button'] as const)(
  '%s 关闭菜单不触发导航',
  (method) => {
    const { navigate, trigger, dialog } = setup();
    if (method === 'cancel')
      fireEvent(dialog, new Event('cancel', { cancelable: true }));
    else if (method === 'backdrop') fireEvent.click(dialog);
    else
      fireEvent.click(
        within(dialog).getByRole('button', { name: '关闭功能导航' }),
      );
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(trigger);
    expect(navigate).not.toHaveBeenCalled();
  },
);
test('菜单首尾焦点循环，Ctrl K 不拦截且不送至背景，宽屏解除菜单', () => {
  const { dialog, trigger } = setup();
  const first = within(dialog).getByRole('button', { name: '关闭功能导航' });
  const last = within(dialog).getByRole('button', { name: '操作日志' });
  last.focus();
  fireEvent.keyDown(last, { key: 'Tab' });
  expect(document.activeElement).toBe(first);
  fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
  expect(document.activeElement).toBe(last);
  const shortcut = new KeyboardEvent('keydown', {
    key: 'k',
    ctrlKey: true,
    cancelable: true,
  });
  fireEvent(window, shortcut);
  expect(shortcut.defaultPrevented).toBe(false);
  expect(dialog.contains(document.activeElement)).toBe(true);
  vi.stubGlobal('innerWidth', 1280);
  fireEvent(window, new Event('resize'));
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
});
test('三个顶部入口切换保留原表单节点，源码与讲解均属于同一工作区', () => {
  function Harness() {
    const [section, setSection] = useState<WorkspaceSection>('explanation');
    return (
      <WorkspaceShell section={section} onSection={setSection}>
        <label>
          草稿
          <input defaultValue="原节点" />
        </label>
      </WorkspaceShell>
    );
  }
  render(<Harness />);
  const draft = screen.getByLabelText('草稿');
  const nav = screen.getByRole('navigation', { name: '主分类导航' });
  expect(within(nav).getAllByRole('button')).toHaveLength(3);
  expect(
    within(nav)
      .getByRole('button', { name: '项目工作区' })
      .getAttribute('aria-current'),
  ).toBe('page');
  fireEvent.click(within(nav).getByRole('button', { name: '操作日志' }));
  fireEvent.click(within(nav).getByRole('button', { name: '项目管理' }));
  fireEvent.click(within(nav).getByRole('button', { name: '项目工作区' }));
  expect(screen.getByLabelText('草稿')).toBe(draft);
  expect(screen.queryByRole('complementary')).toBeNull();
  expect(screen.queryByRole('button', { name: '通知中心' })).toBeNull();
});

test('顶栏无搜索及主题切换，Ctrl和Meta K不拦截也不改变局部焦点', () => {
  const navigate = vi.fn();
  render(
    <WorkspaceShell section="source" onSection={navigate}>
      <label>
        局部草稿
        <input defaultValue="继续编辑" />
      </label>
    </WorkspaceShell>,
  );
  expect(within(screen.getByRole('banner')).queryByRole('textbox')).toBeNull();
  expect(screen.queryByLabelText('搜索当前快照文件')).toBeNull();
  expect(screen.queryByLabelText('搜索项目、快照、文件、接口')).toBeNull();
  expect(screen.queryByRole('button', { name: /切换为.*模式/ })).toBeNull();
  expect(screen.queryByText('Ctrl K')).toBeNull();
  const draft = screen.getByLabelText('局部草稿');
  draft.focus();
  for (const modifier of ['ctrlKey', 'metaKey']) {
    const shortcut = new KeyboardEvent('keydown', {
      key: 'k',
      [modifier]: true,
      cancelable: true,
    });
    fireEvent(window, shortcut);
    expect(shortcut.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(draft);
  }
  expect(draft).toHaveProperty('value', '继续编辑');
  expect(navigate).not.toHaveBeenCalled();
});

test.each(['import', 'source', 'jobs'] as const)(
  '%s 入口移除外壳底栏，保留正文内的源码状态栏',
  (section) => {
    render(
      <WorkspaceShell section={section} onSection={vi.fn()}>
        <h1>页面正文</h1>
        <footer aria-label="源码状态">只读 · 跳转到行</footer>
      </WorkspaceShell>,
    );
    const main = screen.getByRole('main');
    expect(
      within(main).getByRole('heading', { name: '页面正文' }),
    ).toBeTruthy();
    expect(within(main).getByLabelText('源码状态')).toBeTruthy();
    expect(screen.getAllByRole('contentinfo')).toEqual([
      within(main).getByLabelText('源码状态'),
    ]);
    expect(screen.queryByText('项目解读实验室 · 本地单用户工作台')).toBeNull();
    expect(screen.queryByText('源码只读分析 · 模型外发需单次确认')).toBeNull();
  },
);
