import { afterEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { RecordList, type RecordColumn } from './RecordList';

type Record = { id: string; name: string; state: string };
const records: Record[] = [
  { id: 'first', name: '首个项目', state: '可读取' },
  { id: 'last', name: '末尾项目', state: '待分析' },
];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function viewport(initial: boolean) {
  let compact = initial;
  const listeners = new Set<(event: { matches: boolean }) => void>();
  const add = vi.fn(
    (_event: string, listener: (event: { matches: boolean }) => void) =>
      listeners.add(listener),
  );
  const remove = vi.fn(
    (_event: string, listener: (event: { matches: boolean }) => void) =>
      listeners.delete(listener),
  );
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: compact,
    media: query,
    addEventListener: add,
    removeEventListener: remove,
  }));
  return {
    listeners,
    remove,
    change(value: boolean) {
      compact = value;
      act(() => {
        for (const listener of [...listeners]) listener({ matches: compact });
      });
    },
  };
}

function content(items: readonly Record[] = records) {
  const onSelect = vi.fn();
  const title = (record: Record) => (
    <button
      type="button"
      aria-current={record.id === 'first' ? 'true' : undefined}
      onClick={() => onSelect(record.id)}
    >
      {record.name}
    </button>
  );
  const columns: RecordColumn<Record>[] = [
    { key: 'name', title: '名称', render: title },
    { key: 'state', title: '状态', render: (record) => record.state },
  ];
  const view = render(
    <RecordList
      label="项目记录"
      records={items}
      columns={columns}
      rowKey={(record) => record.id}
      recordTitle={title}
      titleColumnKey="name"
      selectedKey="first"
      empty="尚未创建项目。"
    />,
  );
  return { ...view, onSelect };
}

test('桌面表格保留完整记录和原生选择按钮，分页边界以整行标记', () => {
  viewport(false);
  const { container, onSelect } = content();
  const table = screen.getByRole('table', { name: '项目记录' });
  expect(
    within(table).getByRole('columnheader', { name: '名称' }),
  ).toBeTruthy();
  expect(
    within(table).getByRole('columnheader', { name: '状态' }),
  ).toBeTruthy();
  expect(screen.getAllByRole('button', { name: '首个项目' })).toHaveLength(1);
  const selected = screen
    .getByRole('button', { name: '首个项目' })
    .closest('tr');
  expect(selected?.hasAttribute('data-page-keep')).toBe(true);
  expect(selected?.classList.contains('record-list__selected')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: '末尾项目' }));
  expect(onSelect).toHaveBeenCalledWith('last');
  expect(screen.queryByRole('list', { name: '项目记录' })).toBeNull();
  expect(container.querySelector('.ant-pagination')).toBeNull();
  expect(container.querySelector('.ant-table-body')).toBeNull();
});

test('窄屏卡片只有一个选择按钮，主列不重复，其他字段保留名称和值', () => {
  viewport(true);
  const { onSelect } = content();
  const list = screen.getByRole('list', { name: '项目记录' });
  expect(screen.queryByRole('table')).toBeNull();
  expect(screen.getAllByRole('button', { name: '首个项目' })).toHaveLength(1);
  expect(within(list).getAllByText('状态')).toHaveLength(2);
  expect(within(list).getByText('待分析')).toBeTruthy();
  expect(within(list).queryByText('名称')).toBeNull();
  const selected = screen
    .getByRole('button', { name: '首个项目' })
    .closest('li');
  expect(selected?.hasAttribute('data-page-keep')).toBe(true);
  expect(selected?.classList.contains('record-list__selected')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: '末尾项目' }));
  expect(onSelect).toHaveBeenCalledWith('last');
});

test('宽度切换只挂载一种记录布局，卸载后释放媒体查询订阅', () => {
  const media = viewport(false);
  const { unmount } = content();
  media.change(true);
  expect(screen.queryByRole('table')).toBeNull();
  expect(screen.getByRole('list', { name: '项目记录' })).toBeTruthy();
  expect(screen.getAllByRole('button', { name: '末尾项目' })).toHaveLength(1);
  media.change(false);
  expect(screen.getByRole('table', { name: '项目记录' })).toBeTruthy();
  expect(screen.queryByRole('list', { name: '项目记录' })).toBeNull();
  unmount();
  expect(media.listeners.size).toBe(0);
  expect(media.remove).toHaveBeenCalled();
});

test('空记录在两种布局中均使用调用方空状态', () => {
  const media = viewport(false);
  content([]);
  expect(screen.getByText('尚未创建项目。')).toBeTruthy();
  media.change(true);
  expect(screen.getByText('尚未创建项目。')).toBeTruthy();
  expect(screen.queryByRole('button')).toBeNull();
});
