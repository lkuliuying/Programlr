import { afterEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { ContentPager } from './ContentPager';

const originalRects = Object.getOwnPropertyDescriptor(
  Range.prototype,
  'getClientRects',
);
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalRects)
    Object.defineProperty(Range.prototype, 'getClientRects', originalRects);
  else Reflect.deleteProperty(Range.prototype, 'getClientRects');
});

function geometry() {
  let height = 400,
    total = 950;
  let resize = () => {};
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.className === 'paged-viewport' ? height : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.className === 'paged-content' ? total : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
    function (this: HTMLElement) {
      const top = Number(this.dataset.top ?? 0);
      return {
        top,
        bottom: top + 32,
        height: 32,
        width: 100,
        left: 0,
        right: 100,
        x: 0,
        y: top,
        toJSON: () => ({}),
      };
    },
  );
  // jsdom 没有文字排版；真实换行和断点另由浏览器验证。
  Object.defineProperty(Range.prototype, 'getClientRects', {
    configurable: true,
    value: () => [],
  });
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: () => void) {
        resize = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  return {
    change: (nextHeight: number, nextTotal = total) => {
      height = nextHeight;
      total = nextTotal;
      act(() => resize());
    },
  };
}

test('翻页保留同一表单节点和输入，末页与首页按钮正确禁用', () => {
  geometry();
  render(
    <ContentPager label="测试">
      <label>
        草稿
        <input />
      </label>
      <p>后续内容</p>
    </ContentPager>,
  );
  const input = screen.getByRole('textbox');
  fireEvent.change(input, { target: { value: '没有提交的内容' } });
  expect(screen.getByRole('button', { name: '上一页内容' })).toHaveProperty(
    'disabled',
    true,
  );
  fireEvent.click(screen.getByRole('button', { name: '下一页内容' }));
  fireEvent.click(screen.getByRole('button', { name: '下一页内容' }));
  expect(screen.getByRole('button', { name: '下一页内容' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(screen.getByRole('textbox')).toBe(input);
  expect(input).toHaveProperty('value', '没有提交的内容');
});

test('窗口放大或内容减少后夹紧页码，不留下空白尾页', async () => {
  const viewport = geometry();
  render(
    <ContentPager label="测试">
      <p>内容</p>
    </ContentPager>,
  );
  fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });
  viewport.change(1000, 300);
  await waitFor(() =>
    expect(screen.getByRole('combobox')).toHaveProperty('value', '0'),
  );
  expect(screen.getByRole('button', { name: '下一页内容' })).toHaveProperty(
    'disabled',
    true,
  );
});

test('键盘聚焦页外控件自动显示所在页，输入框的翻页键不被接管', () => {
  geometry();
  render(
    <ContentPager label="测试">
      <input aria-label="后续输入" data-top="700" />
      <button data-top="800">末页操作</button>
    </ContentPager>,
  );
  fireEvent.focus(screen.getByRole('button', { name: '末页操作' }));
  expect(screen.getByRole('combobox')).toHaveProperty('value', '2');
  fireEvent.focus(screen.getByRole('textbox'));
  expect(screen.getByRole('combobox')).toHaveProperty('value', '1');
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'PageUp' });
  expect(screen.getByRole('combobox')).toHaveProperty('value', '1');
});

test('模块隐藏再显示保留页码和草稿，数据批次翻页回到内容首页', () => {
  geometry();
  const body = (
    <>
      <input aria-label="草稿" />
      <nav className="workspace-pagination">
        <button>下一批</button>
      </nav>
    </>
  );
  const view = render(<ContentPager label="测试">{body}</ContentPager>);
  fireEvent.click(screen.getByRole('button', { name: '下一页内容' }));
  view.rerender(
    <ContentPager label="测试" active={false}>
      {body}
    </ContentPager>,
  );
  view.rerender(
    <ContentPager label="测试" active>
      {body}
    </ContentPager>,
  );
  expect(screen.getByRole('combobox')).toHaveProperty('value', '1');
  fireEvent.click(screen.getByRole('button', { name: '下一批' }));
  expect(screen.getByRole('combobox')).toHaveProperty('value', '0');
});

test('资源选择改变时回到首页，但不重建表单', () => {
  geometry();
  const body = <input aria-label="草稿" defaultValue="保留" />;
  const view = render(
    <ContentPager label="测试" resetKey="first">
      {body}
    </ContentPager>,
  );
  const input = screen.getByRole('textbox');
  fireEvent.click(screen.getByRole('button', { name: '下一页内容' }));
  view.rerender(
    <ContentPager label="测试" resetKey="second">
      {body}
    </ContentPager>,
  );
  expect(screen.getByRole('combobox')).toHaveProperty('value', '0');
  expect(screen.getByRole('textbox')).toBe(input);
});
