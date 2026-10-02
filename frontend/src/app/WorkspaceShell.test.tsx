import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { WorkspaceShell } from './WorkspaceShell';

const dialogMethods = {
  showModal: Object.getOwnPropertyDescriptor(
    HTMLDialogElement.prototype,
    'showModal',
  ),
  close: Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close'),
};
beforeEach(() => {
  vi.stubGlobal('innerWidth', 390);
  // jsdom 没有浏览器顶层模态行为；焦点约束和遮罩还需真实浏览器验证。
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
  for (const [method, descriptor] of Object.entries(dialogMethods)) {
    if (descriptor)
      Object.defineProperty(HTMLDialogElement.prototype, method, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, method);
  }
});
function setup() {
  const navigate = vi.fn();
  render(
    <WorkspaceShell section="api" onSection={navigate} searchable>
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

test('打开菜单聚焦当前模块，选择后关闭并恢复触发按钮焦点，表单保持', () => {
  const { navigate, trigger, dialog } = setup();
  expect(document.activeElement).toBe(
    within(dialog).getByRole('button', { name: 'API 分析' }),
  );
  expect(trigger.getAttribute('aria-expanded')).toBe('true');
  fireEvent.click(within(dialog).getByRole('button', { name: '源码阅读' }));
  expect(navigate).toHaveBeenCalledExactlyOnceWith('source');
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
  expect(screen.getByLabelText('未提交笔记')).toHaveProperty(
    'value',
    '保留这段文字',
  );
});

test.each(['cancel', 'backdrop', 'button'] as const)(
  '%s 关闭菜单后返回焦点，不触发导航',
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

test('菜单打开时搜索快捷键不移动到背景，放大窗口后解除模态状态', () => {
  const { dialog, navigate, trigger } = setup();
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
  expect(dialog.contains(document.activeElement)).toBe(true);
  vi.stubGlobal('innerWidth', 1280);
  fireEvent(window, new Event('resize'));
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(trigger.getAttribute('aria-expanded')).toBe('false');
  expect(navigate).not.toHaveBeenCalled();
});

test('Tab 和 Shift Tab 在菜单首尾循环，不把焦点送到背景或浏览器工具栏', () => {
  const { dialog } = setup();
  const first = within(dialog).getByRole('button', { name: '关闭功能导航' });
  const last = within(dialog).getByRole('button', { name: '任务历史' });
  last.focus();
  fireEvent.keyDown(last, { key: 'Tab' });
  expect(document.activeElement).toBe(first);
  fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
  expect(document.activeElement).toBe(last);
});
