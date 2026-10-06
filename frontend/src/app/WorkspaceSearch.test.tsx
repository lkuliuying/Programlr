import { afterEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkspaceSearch } from './WorkspaceSearch';
const id = '00000000-0000-0000-0000-000000000001';
const snapshot = '00000000-0000-0000-0000-000000000002';
const analysis = '00000000-0000-0000-0000-000000000003';
const time = '2026-10-03T00:00:00Z';
const project = { id, name: '中文项目', created_at: time };
const endpoint = {
  index: 29,
  method: 'GET',
  path: '/中文/',
  path_kind: 'django_path',
  action: 'list',
  view: null,
  serializer: null,
  model: null,
  evidence: [],
  frontend_available: false,
  frontend_links: [],
};
const clients: QueryClient[] = [];
const panelName = '搜索本地项目与当前上下文';
function mount(options: Partial<Parameters<typeof WorkspaceSearch>[0]> = {}) {
  const props = {
    snapshotId: snapshot,
    analysisId: analysis,
    files: [],
    onProject: vi.fn(),
    onFile: vi.fn(),
    onEndpoint: vi.fn(),
    ...options,
  };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  const view = render(
    <QueryClientProvider client={client}>
      <WorkspaceSearch {...props} />
    </QueryClientProvider>,
  );
  return { ...view, props, client };
}
afterEach(() => {
  cleanup();
  clients.forEach((client) => client.clear());
  clients.length = 0;
  vi.unstubAllGlobals();
});
test('空输入不请求，中文组合结束后防抖查询；分组分页保持q与原接口索引', async () => {
  const fetcher = vi.fn(async (path: string, options: RequestInit = {}) => {
    expect(options.method).toBeUndefined();
    const url = new URL(path, 'http://test');
    expect(url.searchParams.get('q')).toBe('中文');
    const resource = url.pathname;
    const second = url.searchParams.get('page') === '2';
    return new Response(
      JSON.stringify({
        count: 21,
        previous: second
          ? `${resource}?page=1&page_size=20&q=${encodeURIComponent('中文')}`
          : null,
        next: second
          ? null
          : `${resource}?page=2&page_size=20&q=${encodeURIComponent('中文')}`,
        results:
          resource === '/api/v1/projects/'
            ? [{ ...project, name: second ? '中文项目第二批' : project.name }]
            : [endpoint],
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const { props } = mount();
  expect(fetcher).not.toHaveBeenCalled();
  const input = screen.getByRole('textbox', {
    name: '搜索项目、快照、文件、接口',
  });
  expect(screen.getAllByRole('textbox')).toHaveLength(1);
  expect(screen.queryByText('Ctrl K')).toBeNull();
  expect(input.getAttribute('aria-expanded')).toBe('false');
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(screen.queryByRole('dialog')).toBeNull();
  fireEvent.compositionStart(input);
  fireEvent.change(input, { target: { value: '中文' } });
  await new Promise((resolve) => setTimeout(resolve, 250));
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.compositionEnd(input);
  await screen.findByRole('button', { name: 'GET /中文/' });
  fireEvent.click(screen.getAllByRole('button', { name: '下一批记录' })[0]!);
  await screen.findByRole('button', { name: '中文项目第二批' });
  expect(screen.getByRole('textbox')).toBe(input);
  expect(input.getAttribute('aria-controls')).toBe(
    screen.getByRole('region', { name: panelName }).id,
  );
  expect(screen.queryByRole('dialog')).toBeNull();
  fireEvent.click(await screen.findByRole('button', { name: 'GET /中文/' }));
  expect(props.onEndpoint).toHaveBeenCalledWith(
    expect.objectContaining({ index: 29 }),
  );
  expect(input.getAttribute('aria-expanded')).toBe('false');
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(screen.getByRole('textbox')).toBe(input);
  expect(
    fetcher.mock.calls.every(
      ([, options]) => !(options as RequestInit | undefined)?.method,
    ),
  ).toBe(true);
});
test('接口局部失败仍提供项目；文件使用完整清单并独立翻批', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) =>
      path.startsWith('/api/v1/projects/')
        ? new Response(
            JSON.stringify({
              count: 1,
              previous: null,
              next: null,
              results: [project],
            }),
          )
        : new Response(
            JSON.stringify({
              code: 'TEST_FAILED',
              message: '合成接口失败',
              request_id: 'test',
              details: {},
            }),
            { status: 500 },
          ),
    ),
  );
  const files = Array.from({ length: 21 }, (_, index) => ({
    id: String(index),
    snapshot_id: snapshot,
    file_path: `中文/${index}.py`,
    sha256: 'a'.repeat(64),
    size_bytes: 1,
    line_count: 4,
    encoding: 'utf-8',
  }));
  const { props } = mount({ files });
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '中文' } });
  await screen.findByText('合成接口失败');
  fireEvent.click(screen.getAllByRole('button', { name: '下一批记录' })[1]!);
  expect(screen.getByRole('button', { name: '中文项目' })).toBeTruthy();
  fireEvent.click(await screen.findByRole('button', { name: '中文/20.py' }));
  expect(props.onFile).toHaveBeenCalledWith(files[20]);
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
});
test.each(['', ' \t\u3000 '])(
  '空输入或纯空白不因聚焦、点击和快捷键显示下拉：%j',
  async (value) => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    mount();
    const input = screen.getByRole('textbox');
    act(() => input.focus());
    fireEvent.change(input, { target: { value } });
    fireEvent.click(input);
    fireEvent.keyDown(input, { key: 'k', ctrlKey: true });
    fireEvent.keyDown(input, { key: 'k', metaKey: true });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowUp' });
    expect(screen.queryByRole('region', { name: panelName })).toBeNull();
    expect(input.getAttribute('aria-expanded')).toBe('false');
    await new Promise((resolve) => setTimeout(resolve, 250));
    expect(screen.queryByRole('region', { name: panelName })).toBeNull();
    expect(fetcher).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(input);
  },
);

test('输入后在防抖期间点击外部，不延迟展开或发起查询', async () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  const outside = document.createElement('button');
  document.body.append(outside);
  mount();
  const input = screen.getByRole('textbox');
  act(() => input.focus());
  fireEvent.change(input, { target: { value: '中文' } });
  fireEvent.pointerDown(outside);
  expect(document.activeElement).toBe(input);
  await new Promise((resolve) => setTimeout(resolve, 250));
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(fetcher).not.toHaveBeenCalled();
  outside.remove();
});

test('顶栏可直接输入，展开不隔离背景，Escape关闭后保留同一输入框和焦点', async () => {
  const fetcher = vi.fn(
    async () =>
      new Response(
        JSON.stringify({ count: 0, previous: null, next: null, results: [] }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  const trigger = document.createElement('button');
  document.body.append(trigger);
  trigger.focus();
  mount({
    snapshotId: null,
    analysisId: null,
  });
  const input = screen.getByRole('textbox', {
    name: '搜索项目、快照、文件、接口',
  });
  expect(document.activeElement).toBe(trigger);
  act(() => input.focus());
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  fireEvent.change(input, { target: { value: '中文' } });
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  await screen.findByRole('region', { name: panelName });
  expect(trigger.inert).not.toBe(true);
  expect(screen.queryByRole('dialog')).toBeNull();
  fireEvent.keyDown(input, { key: 'Escape' });
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(screen.getByRole('textbox')).toBe(input);
  expect(document.activeElement).toBe(input);
  fireEvent.keyDown(input, { key: 'k', ctrlKey: true });
  expect(screen.getByRole('region', { name: panelName })).toBeTruthy();
  fireEvent.keyDown(input, { key: 'Escape' });
  fireEvent.click(input);
  expect(screen.getByRole('region', { name: panelName })).toBeTruthy();
  fireEvent.compositionStart(input);
  fireEvent.keyDown(input, { key: 'Escape' });
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  fireEvent.compositionEnd(input);
  expect(screen.getByRole('region', { name: panelName })).toBeTruthy();
  expect(fetcher).toHaveBeenCalled();
  trigger.remove();
});

test('搜索结果保留上下箭头循环，Escape从结果返回顶栏且不触发导航', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async (path: string) =>
        new Response(
          JSON.stringify({
            count: 1,
            previous: null,
            next: null,
            results: path.startsWith('/api/v1/projects/')
              ? [project]
              : [endpoint],
          }),
        ),
    ),
  );
  const { props } = mount({
    files: [
      {
        id: 'file',
        snapshot_id: snapshot,
        file_path: '中文.py',
        sha256: 'a'.repeat(64),
        size_bytes: 1,
        line_count: 4,
        encoding: 'utf-8',
      },
    ],
  });
  const input = screen.getByRole('textbox');
  act(() => input.focus());
  fireEvent.change(input, { target: { value: '中文' } });
  const last = await screen.findByRole('button', { name: 'GET /中文/' });
  const first = screen.getByRole('button', { name: '中文项目' });
  fireEvent.keyDown(input, { key: 'ArrowDown' });
  expect(document.activeElement).toBe(first);
  fireEvent.keyDown(first, { key: 'ArrowUp' });
  expect(document.activeElement).toBe(last);
  fireEvent.keyDown(last, { key: 'ArrowDown' });
  expect(document.activeElement).toBe(first);
  act(() => input.focus());
  fireEvent.keyDown(input, { key: 'ArrowUp' });
  expect(document.activeElement).toBe(last);
  fireEvent.keyDown(last, { key: 'Escape' });
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(document.activeElement).toBe(input);
  expect(input).toHaveProperty('value', '中文');
  expect(props.onProject).not.toHaveBeenCalled();
  expect(props.onFile).not.toHaveBeenCalled();
  expect(props.onEndpoint).not.toHaveBeenCalled();
});

test('结果内转移焦点保持展开，Tab可离开，外部点击和焦点离开关闭下拉', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async (path: string) =>
        new Response(
          JSON.stringify({
            count: path.startsWith('/api/v1/projects/') ? 1 : 0,
            previous: null,
            next: null,
            results: path.startsWith('/api/v1/projects/') ? [project] : [],
          }),
        ),
    ),
  );
  const outside = document.createElement('button');
  document.body.append(outside);
  mount();
  const input = screen.getByRole('textbox');
  act(() => input.focus());
  fireEvent.change(input, { target: { value: '中文' } });
  const result = await screen.findByRole('button', { name: '中文项目' });
  act(() => result.focus());
  expect(screen.getByRole('region', { name: panelName })).toBeTruthy();
  const tab = new KeyboardEvent('keydown', {
    key: 'Tab',
    bubbles: true,
    cancelable: true,
  });
  fireEvent(result, tab);
  expect(tab.defaultPrevented).toBe(false);
  act(() => outside.focus());
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  act(() => input.focus());
  expect(screen.getByRole('region', { name: panelName })).toBeTruthy();
  fireEvent.pointerDown(outside);
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
  expect(input).toHaveProperty('value', '中文');
  outside.remove();
});

test('Unicode关键词按字符限制到200个并以只读GET查询', async () => {
  const query = '😀'.repeat(200);
  const fetcher = vi.fn(async (path: string, options: RequestInit = {}) => {
    expect(new URL(path, 'http://test').searchParams.get('q')).toBe(query);
    expect(options.method).toBeUndefined();
    return new Response(
      JSON.stringify({ count: 0, previous: null, next: null, results: [] }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  mount();
  const input = screen.getByRole('textbox');
  fireEvent.change(input, { target: { value: `${query}多余` } });
  expect(input).toHaveProperty('value', query);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  expect(screen.getByRole('textbox')).toBe(input);
});

test('快照名称搜索覆盖全部项目，选择同时传递项目与快照且无写请求', async () => {
  const item = {
    id: snapshot,
    project_id: id,
    name: '中文版本',
    job_id: analysis,
    created_at: time,
    source_extensions: ['.py'],
    summary: {
      entries: 1,
      accepted: 1,
      excluded: 0,
      skipped: 0,
      rejected: 0,
      declared_bytes: 4,
      extracted_bytes: 4,
      reasons: {},
    },
  };
  const fetcher = vi.fn(async (path: string, options: RequestInit = {}) => {
    expect(options.method).toBeUndefined();
    const url = new URL(path, 'http://test');
    return new Response(
      JSON.stringify({
        count: url.pathname === '/api/v1/snapshots/' ? 1 : 0,
        next: null,
        previous: null,
        results:
          url.pathname === '/api/v1/snapshots/'
            ? [{ snapshot: item, project }]
            : [],
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const onSnapshot = vi.fn();
  mount({ snapshotId: null, analysisId: null, onSnapshot });
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '中文' } });
  fireEvent.click(
    await screen.findByRole('button', { name: /中文版本.*中文项目/ }),
  );
  expect(onSnapshot).toHaveBeenCalledWith(
    expect.objectContaining({ id: snapshot }),
    project,
  );
  expect(
    fetcher.mock.calls.some(([path]) => path.startsWith('/api/v1/snapshots/?')),
  ).toBe(true);
  expect(screen.queryByRole('region', { name: panelName })).toBeNull();
});
