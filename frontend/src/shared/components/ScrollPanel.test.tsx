import { afterEach, expect, test } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createPortal } from 'react-dom';
import { ScrollPanel } from './ScrollPanel';

afterEach(cleanup);
test('面板隐藏与显示保留节点、草稿及滚动位置，不再按屏切页', () => {
  const body = <input aria-label="草稿" />;
  const view = render(<ScrollPanel label="阅读">{body}</ScrollPanel>);
  const panel = screen.getByRole('region', { name: '阅读' });
  const input = screen.getByLabelText('草稿');
  fireEvent.change(input, { target: { value: '未提交内容' } });
  panel.scrollTop = 320;
  view.rerender(
    <ScrollPanel label="阅读" active={false}>
      {body}
    </ScrollPanel>,
  );
  view.rerender(<ScrollPanel label="阅读">{body}</ScrollPanel>);
  expect(screen.getByLabelText('草稿')).toBe(input);
  expect(input).toHaveProperty('value', '未提交内容');
  expect(panel.scrollTop).toBe(320);
  expect(screen.queryByText('下一页内容')).toBeNull();
  const event = new KeyboardEvent('keydown', {
    key: 'PageDown',
    bubbles: true,
    cancelable: true,
  });
  input.dispatchEvent(event);
  expect(event.defaultPrevented).toBe(false);
});
test('资源变化或真实数据翻页回到顶部而不重建表单', () => {
  const body = (
    <>
      <input aria-label="草稿" defaultValue="保留" />
      <nav className="workspace-pagination">
        <button>下一批</button>
      </nav>
    </>
  );
  const view = render(
    <ScrollPanel label="记录" resetKey="one">
      {body}
    </ScrollPanel>,
  );
  const panel = screen.getByRole('region');
  const input = screen.getByLabelText('草稿');
  panel.scrollTop = 200;
  view.rerender(
    <ScrollPanel label="记录" resetKey="two">
      {body}
    </ScrollPanel>,
  );
  expect(panel.scrollTop).toBe(0);
  expect(screen.getByLabelText('草稿')).toBe(input);
  panel.scrollTop = 200;
  fireEvent.click(screen.getByText('下一批'));
  expect(panel.scrollTop).toBe(0);
});
test('Portal 焦点和点击不改变正文滚动', () => {
  render(
    <ScrollPanel label="日志">
      <p>记录</p>
      {createPortal(
        <nav className="workspace-pagination">
          <button>弹层操作</button>
          <input aria-label="弹层筛选" />
        </nav>,
        document.body,
      )}
    </ScrollPanel>,
  );
  const panel = screen.getByRole('region');
  panel.scrollTop = 300;
  fireEvent.focus(screen.getByLabelText('弹层筛选'));
  fireEvent.click(screen.getByText('弹层操作'));
  expect(panel.scrollTop).toBe(300);
});
