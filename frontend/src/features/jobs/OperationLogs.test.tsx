import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { OperationLogs } from './OperationLogs';
import type { OperationLog } from '../../shared/api/generated/schema';

const first: OperationLog = {
  id: '00000000-0000-0000-0000-000000000001',
  display_id: 41,
  operation: 'import',
  result: 'succeeded',
  request_id: 'request-test',
  source_kind: 'zip',
  job_id: null,
  job: null,
  project_id: '00000000-0000-0000-0000-000000000010',
  project_name: '日志测试项目',
  snapshot_id: null,
  object_name: '示例源码',
  error_code: '',
  events: [],
  result_deleted: false,
  created_at: '2026-10-03T00:00:00Z',
  updated_at: '2026-10-03T04:00:00Z',
  started_at: '2026-10-03T00:00:00Z',
  ended_at: '2026-10-03T00:05:00Z',
  retry_action: 'none',
  retry_reason: '仅失败的操作记录可恢复任务。',
  project_available: true,
};
const clients: QueryClient[] = [];
beforeEach(() => {
  // jsdom 缺少尺寸观察器；这里只验证交互，真实布局另由浏览器验收。
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
    },
  );
});
afterEach(() => {
  vi.useRealTimers();
  cleanup();
  for (const client of clients) client.clear();
  clients.length = 0;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mount(
  records: OperationLog[] = [first],
  count = records.length,
  active = true,
  respond?: (
    query: URLSearchParams,
    options?: RequestInit,
  ) => Response | Promise<Response>,
  respondRoute?: (
    path: string,
    options?: RequestInit,
  ) => Response | Promise<Response> | undefined,
) {
  const fetcher = vi.fn(
    async (input: string | URL | Request, options?: RequestInit) => {
      const path = String(input);
      const routeResponse = respondRoute?.(path, options);
      if (routeResponse !== undefined) return routeResponse;
      if (path === `/api/v1/operation-logs/${first.id}/`)
        return new Response(JSON.stringify(first));
      const params = new URL(path, 'http://localhost').searchParams;
      if (path.startsWith('/api/v1/operation-logs/statistics/'))
        return new Response(
          JSON.stringify({
            as_of: first.created_at,
            count,
            failed_count: records.filter((item) => item.result === 'failed')
              .length,
            active_count: records.filter((item) =>
              ['submitted', 'accepted', 'running'].includes(item.result),
            ).length,
            retryable_count: records.filter(
              (item) => item.retry_action !== 'none',
            ).length,
            recent_success_rate: 80,
            previous_success_rate: 60,
            success_rate_change_pp: 20,
            recent_window: { start: first.created_at, end: first.ended_at },
            previous_window: { start: first.created_at, end: first.ended_at },
            trend: [],
          }),
        );
      if (path.includes('/related/') || path.includes('/history/'))
        return new Response(
          JSON.stringify({ count: 0, results: [], next: null, previous: null }),
        );
      if (path.startsWith('/api/v1/operation-logs/export/'))
        return new Response('\ufeff日志编号,操作\r\n41,导入\r\n', {
          headers: { 'Content-Type': 'text/csv' },
        });
      if (respond) return respond(params, options);
      const page = Number(params.get('page'));
      const pageSize = Number(params.get('page_size'));
      const link = (value: number) => {
        const query = new URLSearchParams(params);
        query.set('page', String(value));
        return '/api/v1/operation-logs/?' + query.toString();
      };
      return new Response(
        JSON.stringify({
          count,
          results: records,
          next: page * pageSize < count ? link(page + 1) : null,
          previous: page > 1 ? link(page - 1) : null,
        }),
      );
    },
  );
  vi.stubGlobal('fetch', fetcher);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  const onJob = vi.fn();
  const page = (visible: boolean) => (
    <QueryClientProvider client={client}>
      <OperationLogs active={visible} jobId={null} onJob={onJob} />
    </QueryClientProvider>
  );
  const view = render(page(active));
  return Object.assign(fetcher, {
    client,
    setActive: (visible: boolean) => view.rerender(page(visible)),
  });
}
function lastQuery(fetcher: ReturnType<typeof mount>) {
  const calls = fetcher.mock.calls
    .map(([path]) => String(path))
    .filter((path) => path.startsWith('/api/v1/operation-logs/?'));
  return new URL(calls.at(-1)!, 'http://localhost').searchParams;
}
async function valueFilter(label: string, value: string) {
  fireEvent.click(screen.getByRole('button', { name: `${label}筛选` }));
  const dialog = await screen.findByRole('dialog', {
    name: `${label}筛选条件`,
  });
  fireEvent.change(within(dialog).getByLabelText(`${label}条件`), {
    target: { value },
  });
  fireEvent.click(
    within(dialog).getByRole('button', { name: `应用${label}筛选` }),
  );
}
async function timeFilter(label: string, after: string, before: string) {
  fireEvent.click(screen.getByRole('button', { name: `${label}筛选` }));
  const dialog = await screen.findByRole('dialog', {
    name: `${label}筛选条件`,
  });
  setTimeInput(within(dialog).getByLabelText(`${label}从`), after);
  setTimeInput(within(dialog).getByLabelText(`${label}至`), before);
  fireEvent.click(
    within(dialog).getByRole('button', { name: `应用${label}筛选` }),
  );
  return dialog;
}
function setTimeInput(input: HTMLElement, value: string) {
  fireEvent.change(input, {
    target: {
      value: value.replace('T', ' ') + (value.length === 16 ? ':00' : ''),
    },
  });
  fireEvent.blur(input);
}

function listResponse(
  records: OperationLog[],
  count = records.length,
  query = new URLSearchParams({ page: '1', page_size: '20' }),
) {
  const page = Number(query.get('page'));
  const pageSize = Number(query.get('page_size'));
  const link = (value: number) => {
    const parameters = new URLSearchParams(query);
    parameters.set('page', String(value));
    return '/api/v1/operation-logs/?' + parameters;
  };
  return new Response(
    JSON.stringify({
      count,
      results: records,
      next: page * pageSize < count ? link(page + 1) : null,
      previous: page > 1 ? link(page - 1) : null,
    }),
  );
}

function apiFailure(code: string, message: string, status = 500) {
  return new Response(
    JSON.stringify({ code, message, request_id: 'request-test', details: {} }),
    { status },
  );
}

async function changePageSize(size: number) {
  const control = screen.getByRole('combobox', { name: '每页日志数量' });
  if (control instanceof HTMLSelectElement) {
    fireEvent.change(control, { target: { value: String(size) } });
    return;
  }
  fireEvent.mouseDown(control);
  const option = await screen.findByRole('option', {
    name: new RegExp(`^${size}(?:\\s|$)`),
  });
  fireEvent.click(option);
}

function downloadSpies() {
  const createObjectURL = vi.fn((blob: Blob) => {
    expect(blob.type).toContain('text/csv');
    return 'blob:operation-export';
  });
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURL,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: revokeObjectURL,
  });
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  return { createObjectURL, revokeObjectURL, click };
}

async function findLogDetails(displayId: number) {
  const drawer = await screen.findByRole('dialog', { name: '操作详情' });
  const label = await within(drawer).findByText('日志 ID');
  expect(label.nextElementSibling?.textContent).toBe(String(displayId));
  return drawer;
}

function expectLogDetails(displayId: number) {
  const drawer = screen.getByRole('dialog', { name: '操作详情' });
  expect(
    within(drawer).getByText('日志 ID').nextElementSibling?.textContent,
  ).toBe(String(displayId));
}

test('表格显示准确的两种时间、运行中空值、历史摘要和已删除结果', async () => {
  mount([
    first,
    {
      ...first,
      id: '00000000-0000-0000-0000-000000000002',
      display_id: 42,
      result: 'running',
      ended_at: null,
    },
    {
      ...first,
      id: '00000000-0000-0000-0000-000000000003',
      display_id: 43,
      result_deleted: true,
      events: [{ legacy: true }],
    },
    {
      ...first,
      id: '00000000-0000-0000-0000-000000000004',
      display_id: 44,
      ended_at: null,
    },
  ]);
  const table = await screen.findByRole('table', { name: '操作日志表格' });
  await within(table).findByText('尚未结束');
  expect(within(table).getByText('未记录')).toBeTruthy();
  expect(within(table).getByText('历史摘要')).toBeTruthy();
  expect(within(table).getByText('结果已删除')).toBeTruthy();
  const row = within(table).getAllByRole('row')[1]!;
  expect(row.querySelectorAll('time')[0]?.dateTime).toBe(first.started_at);
  expect(row.querySelectorAll('time')[1]?.dateTime).toBe(first.ended_at);
  expect(row.textContent).not.toContain(
    new Date(first.updated_at).toLocaleString('zh-CN'),
  );
  for (const label of ['操作类型', '结果', '开始时间', '结束时间'])
    expect(
      screen.getByRole('button', { name: `${label}筛选` }).closest('th'),
    ).toBeTruthy();
  expect(document.querySelector('.operation-filter-hint')).toBeNull();
  expect(
    document.querySelectorAll('.operation-filters .operation-column-heading'),
  ).toHaveLength(0);
});

test('四列组合筛选传递到服务端，改变条件复位批次，分页携带全部条件', async () => {
  const fetcher = mount([first], 41);
  await screen.findByText(/^共 41 条操作记录/);
  fireEvent.click(screen.getByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  fireEvent.change(screen.getByRole('textbox', { name: '搜索操作日志' }), {
    target: { value: '示例' },
  });
  await waitFor(() => expect(lastQuery(fetcher).get('q')).toBe('示例'));
  await valueFilter('操作类型', 'import');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('operation')).toBe('import'),
  );
  expect(lastQuery(fetcher).get('page')).toBe('1');
  await valueFilter('结果', 'succeeded');
  await timeFilter('开始时间', '2026-10-03T08:00', '2026-10-03T09:00');
  await timeFilter('结束时间', '2026-10-03T08:05', '2026-10-03T10:00');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('ended_after')).toBe(
      new Date('2026-10-03T08:05').toISOString(),
    ),
  );
  fireEvent.click(screen.getByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  expect(Object.fromEntries(lastQuery(fetcher))).toEqual({
    page: '2',
    page_size: '20',
    q: '示例',
    operation: 'import',
    result: 'succeeded',
    started_after: new Date('2026-10-03T08:00').toISOString(),
    started_before: new Date('2026-10-03T09:00').toISOString(),
    ended_after: new Date('2026-10-03T08:05').toISOString(),
    ended_before: new Date('2026-10-03T10:00').toISOString(),
  });
  fireEvent.click(screen.getByRole('button', { name: '清除全部筛选' }));
  await waitFor(() =>
    expect(Object.fromEntries(lastQuery(fetcher))).toEqual({
      page: '1',
      page_size: '20',
    }),
  );
});

test('时间反序阻止请求，支持单端范围，清除单列不影响其他条件', async () => {
  const fetcher = mount();
  await screen.findByText(/^共 1 条操作记录/);
  await valueFilter('操作类型', 'import');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('operation')).toBe('import'),
  );
  const before = fetcher.mock.calls.length;
  const dialog = await timeFilter(
    '结束时间',
    '2026-10-04T10:00',
    '2026-10-03T10:00',
  );
  expect(within(dialog).getByRole('alert').textContent).toBe(
    '时间上界不能早于下界。',
  );
  expect(fetcher.mock.calls.length).toBe(before);
  setTimeInput(within(dialog).getByLabelText('结束时间从'), '');
  fireEvent.click(
    within(dialog).getByRole('button', { name: '应用结束时间筛选' }),
  );
  await waitFor(() =>
    expect(lastQuery(fetcher).get('ended_before')).toBe(
      new Date('2026-10-03T10:00').toISOString(),
    ),
  );
  expect(lastQuery(fetcher).has('ended_after')).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: '结束时间筛选' }));
  const clear = await screen.findByRole('dialog', { name: '结束时间筛选条件' });
  fireEvent.click(
    within(clear).getByRole('button', { name: '清除结束时间筛选' }),
  );
  await waitFor(() =>
    expect(lastQuery(fetcher).has('ended_before')).toBe(false),
  );
  expect(lastQuery(fetcher).get('operation')).toBe('import');
});

test('中文日历选择日期保留时分秒，外层应用前不改变查询', async () => {
  const fetcher = mount();
  await screen.findByText(/^共 1 条操作记录/);
  fireEvent.click(screen.getByRole('button', { name: '开始时间筛选' }));
  const dialog = await screen.findByRole('dialog', {
    name: '开始时间筛选条件',
  });
  const input = within(dialog).getByLabelText('开始时间从');
  setTimeInput(input, '2026-10-03T08:00:12');
  fireEvent.click(input);
  await screen.findByRole('columnheader', { name: '日' });
  fireEvent.click(screen.getByTitle('2026-10-04'));
  expect(lastQuery(fetcher).has('started_after')).toBe(false);
  fireEvent.click(within(dialog).getByRole('button', { name: /^确\s*定$/ }));
  expect(lastQuery(fetcher).has('started_after')).toBe(false);
  fireEvent.click(
    within(dialog).getByRole('button', { name: '应用开始时间筛选' }),
  );
  await waitFor(() =>
    expect(lastQuery(fetcher).get('started_after')).toBe(
      new Date('2026-10-04T08:00:12').toISOString(),
    ),
  );
  expect(lastQuery(fetcher).has('started_before')).toBe(false);
});

test('日志详情保留，应用筛选清除旧选择，Escape关闭筛选并恢复焦点', async () => {
  mount();
  fireEvent.click(
    await screen.findByRole('button', { name: '查看源码导入日志详情' }),
  );
  await findLogDetails(first.display_id);
  await valueFilter('结果', 'succeeded');
  await waitFor(() => expect(screen.queryByText('日志 ID')).toBeNull());
  const trigger = screen.getByRole('button', {
    name: '开始时间筛选',
  });
  fireEvent.click(trigger);
  const dialog = await screen.findByRole('dialog', {
    name: '开始时间筛选条件',
  });
  const input = within(dialog).getByLabelText('开始时间从');
  input.focus();
  fireEvent.keyDown(input, { key: 'Escape' });
  await waitFor(() =>
    expect(trigger.getAttribute('aria-expanded')).toBe('false'),
  );
  expect(document.activeElement).toBe(trigger);
});

test('未激活页面不读取日志', () => {
  const fetcher = mount([], 0, false);
  expect(fetcher).not.toHaveBeenCalled();
});

test('表格溢出时顶部横向控件可直接访问右侧时间列', async () => {
  vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.className === 'operation-table' ? 1102 : 0;
    },
  );
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockImplementation(
    function (this: HTMLElement) {
      return this.className === 'operation-table' ? 360 : 0;
    },
  );
  mount();
  const slider = await screen.findByRole('slider', {
    name: '操作日志横向位置',
  });
  fireEvent.change(slider, { target: { value: '75' } });
  const table = screen.getByRole('region', { name: '操作日志表格区域' });
  expect(table.scrollLeft).toBe(556.5);
  expect(slider).toHaveProperty('value', '75');
  table.scrollLeft = 0;
  fireEvent.scroll(table);
  expect(slider).toHaveProperty('value', '0');
});

test('固定编号跨批次与搜索保持，详情展示编号而非 UUID，默认查询全部项目', async () => {
  const second = {
    ...first,
    id: '00000000-0000-0000-0000-000000000099',
    display_id: 137,
    object_name: '另一项目源码',
  };
  const fetcher = mount([first], 21, true, (params) => {
    const filtered = !!params.get('q');
    const page = Number(params.get('page'));
    return new Response(
      JSON.stringify({
        count: filtered ? 1 : 21,
        results: page === 2 ? [second] : [first],
        next:
          !filtered && page === 1
            ? '/api/v1/operation-logs/?page=2&page_size=20'
            : null,
        previous:
          page === 2 ? '/api/v1/operation-logs/?page=1&page_size=20' : null,
      }),
    );
  });
  const table = await screen.findByRole('table', { name: '操作日志表格' });
  await within(table).findByText('41');
  expect(within(table).getAllByRole('columnheader')[0]?.textContent).toBe('ID');
  expect(
    within(table).getAllByRole('row')[1]?.querySelector('td')?.textContent,
  ).toBe('41');
  expect(screen.queryByLabelText('项目 ID')).toBeNull();
  expect(lastQuery(fetcher).has('project_id')).toBe(false);
  fireEvent.click(screen.getByTitle('下一页'));
  await within(table).findByText('137');
  fireEvent.click(screen.getByTitle('上一页'));
  await within(table).findByText('41');
  fireEvent.change(screen.getByRole('textbox', { name: '搜索操作日志' }), {
    target: { value: '示例' },
  });
  await waitFor(() => expect(lastQuery(fetcher).get('q')).toBe('示例'));
  await screen.findByText(/^共 1 条操作记录/);
  expect(
    within(table).getAllByRole('row')[1]?.querySelector('td')?.textContent,
  ).toBe('41');
  fireEvent.click(screen.getByRole('button', { name: '查看源码导入日志详情' }));
  await findLogDetails(41);
  expect(document.body.textContent).not.toContain(first.id);
  expect(document.body.textContent).not.toContain(first.project_id);
  expect(
    fetcher.mock.calls.some(
      ([path]) => String(path) === `/api/v1/operation-logs/${first.id}/`,
    ),
  ).toBe(true);
});

test('搜索防抖200ms，换词复位并清除详情，清空即时恢复且保留列筛选', async () => {
  const fetcher = mount([first], 21);
  await screen.findByText(/^共 21 条操作记录/);
  await valueFilter('结果', 'succeeded');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('result')).toBe('succeeded'),
  );
  fireEvent.click(await screen.findByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  fireEvent.click(
    await screen.findByRole('button', { name: '查看源码导入日志详情' }),
  );
  await findLogDetails(41);
  const input = screen.getByRole('textbox', { name: '搜索操作日志' });
  vi.useFakeTimers();
  const before = fetcher.mock.calls.length;
  fireEvent.change(input, { target: { value: '示' } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(150);
  });
  fireEvent.change(input, { target: { value: ' 示例 ' } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(199);
  });
  expect(fetcher.mock.calls.length).toBe(before);
  expect(screen.queryByText('日志 ID')).toBeNull();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(Object.fromEntries(lastQuery(fetcher))).toEqual({
    page: '1',
    page_size: '20',
    q: '示例',
    result: 'succeeded',
  });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: '清除日志搜索' }));
  });
  expect(input).toHaveProperty('value', '');
  expect(document.activeElement).toBe(input);
  expect(Object.fromEntries(lastQuery(fetcher))).toEqual({
    page: '1',
    page_size: '20',
    result: 'succeeded',
  });
});

test('中文组合输入完成后才搜索，名称限制200个 Unicode 字符且不截断代理对', async () => {
  const fetcher = mount();
  await screen.findByText(/^共 1 条操作记录/);
  const input = screen.getByRole('textbox', { name: '搜索操作日志' });
  vi.useFakeTimers();
  const before = fetcher.mock.calls.length;
  fireEvent.compositionStart(input);
  fireEvent.change(input, { target: { value: '导' } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
  fireEvent.change(input, { target: { value: '导入' } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
  expect(fetcher.mock.calls.length).toBe(before);
  fireEvent.compositionEnd(input, { data: '导入' });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(199);
  });
  expect(fetcher.mock.calls.length).toBe(before);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1);
  });
  expect(lastQuery(fetcher).get('q')).toBe('导入');
  fireEvent.change(input, { target: { value: '😀'.repeat(201) } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(200);
  });
  expect(input).toHaveProperty('value', '😀'.repeat(200));
  expect(lastQuery(fetcher).get('q')).toBe('😀'.repeat(200));
  expect([...(lastQuery(fetcher).get('q') ?? '')]).toHaveLength(200);
});

test('换词立即取消旧读取，迟到旧搜索结果不能覆盖新结果', async () => {
  let oldSignal: AbortSignal | null | undefined;
  let finishOld: ((response: Response) => void) | undefined;
  const current = { ...first, display_id: 92, object_name: '新搜索结果' };
  const response = (record: OperationLog) =>
    new Response(
      JSON.stringify({
        count: 1,
        results: [record],
        next: null,
        previous: null,
      }),
    );
  const fetcher = mount([first], 1, true, (params, options) => {
    if (params.get('q') === '旧') {
      oldSignal = options?.signal;
      return new Promise<Response>((resolve) => {
        finishOld = resolve;
      });
    }
    return response(params.get('q') === '新' ? current : first);
  });
  await screen.findByText(/^共 1 条操作记录/);
  const input = screen.getByRole('textbox', { name: '搜索操作日志' });
  fireEvent.change(input, { target: { value: '旧' } });
  await waitFor(() => expect(oldSignal).toBeInstanceOf(AbortSignal));
  fireEvent.change(input, { target: { value: '新' } });
  expect(oldSignal?.aborted).toBe(true);
  await screen.findByText('新搜索结果');
  await act(async () => {
    finishOld?.(response({ ...first, object_name: '迟到旧结果' }));
  });
  expect(screen.queryByText('迟到旧结果')).toBeNull();
  expect(screen.getByText('新搜索结果')).toBeTruthy();
  expect(lastQuery(fetcher).get('q')).toBe('新');
});

test.each([0, 1.5, Number.MAX_SAFE_INTEGER + 1, undefined])(
  '响应编号 %s 无效时明确失败，不显示伪编号',
  async (displayId) => {
    mount(
      [],
      0,
      true,
      () =>
        new Response(
          JSON.stringify({
            count: 1,
            results: [{ ...first, display_id: displayId }],
            next: null,
            previous: null,
          }),
        ),
    );
    await screen.findByText('响应结构或资源归属无效。');
    expect(screen.queryByText('示例源码')).toBeNull();
  },
);

test('统计使用完整查询总数，快捷视图与排序改变服务端筛选而不影响统计范围', async () => {
  const fetcher = mount([first], 1284);
  const metrics = screen.getByLabelText('操作日志统计');
  await within(metrics).findByText('1,284');
  expect(within(metrics).getByText('80%')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: '失败 (0)' }));
  await waitFor(() => expect(lastQuery(fetcher).get('view')).toBe('failed'));
  fireEvent.change(screen.getByLabelText('日志排序'), {
    target: { value: 'ended_at' },
  });
  await waitFor(() =>
    expect(lastQuery(fetcher).get('ordering')).toBe('ended_at'),
  );
  await valueFilter('结果', 'succeeded');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('result')).toBe('succeeded'),
  );
  expect(lastQuery(fetcher).has('view')).toBe(false);
  for (const [path] of fetcher.mock.calls.filter(([path]) =>
    String(path).includes('/statistics/'),
  )) {
    const params = new URL(String(path), 'http://localhost').searchParams;
    expect(
      params.has('result') || params.has('view') || params.has('page'),
    ).toBe(false);
  }
});

test('右侧详情读取关联历史，切换关联详情保留焦点，关闭后返回所选记录', async () => {
  let showRelated = false;
  const related = {
    ...first,
    id: '00000000-0000-0000-0000-000000000002',
    display_id: 42,
    object_name: '关联操作对象',
    relation: 'child',
  };
  const fetcher = mount([first], 1, true, undefined, (path) => {
    if (path === `/api/v1/operation-logs/${related.id}/`)
      return new Response(JSON.stringify(related));
    if (
      showRelated &&
      path.startsWith(`/api/v1/operation-logs/${first.id}/related/`)
    )
      return listResponse([related]);
  });
  const trigger = await screen.findByRole('button', {
    name: '查看源码导入日志详情',
  });
  fireEvent.click(trigger);
  await findLogDetails(41);
  await screen.findByText('暂无关联任务。');
  await waitFor(() =>
    expect(
      screen
        .getByRole('dialog', { name: '操作详情' })
        .contains(document.activeElement),
    ).toBe(true),
  );
  expect(
    fetcher.mock.calls.some(([path]) => String(path).includes('/history/')),
  ).toBe(true);
  expect(
    screen.getByRole('link', { name: '查看相关项目' }).getAttribute('href'),
  ).toContain('section=import');
  showRelated = true;
  await act(async () => {
    await fetcher.client.refetchQueries({
      queryKey: ['operation-logs', 'related', first.id],
      type: 'active',
    });
  });
  const relatedTrigger = await screen.findByRole('button', {
    name: /后续任务 · 42/,
  });
  relatedTrigger.focus();
  fireEvent.click(relatedTrigger);
  const drawer = await findLogDetails(related.display_id);
  const close = within(drawer).getByRole('button', { name: '关闭操作详情' });
  await waitFor(() => expect(document.activeElement).toBe(close));
  expect(within(drawer).getByText('关联操作对象')).toBeTruthy();
  fireEvent.click(close);
  await waitFor(() => expect(screen.queryByText('日志 ID')).toBeNull());
  await waitFor(() => expect(document.activeElement).toBe(trigger));
});

test('详情关闭按钮可用Escape关闭抽屉并恢复触发按钮焦点', async () => {
  mount();
  const trigger = await screen.findByRole('button', {
    name: '查看源码导入日志详情',
  });
  trigger.focus();
  fireEvent.click(trigger);
  const drawer = await findLogDetails(first.display_id);
  const close = within(drawer).getByRole('button', { name: '关闭操作详情' });
  close.focus();
  fireEvent.keyDown(close, { key: 'Escape', keyCode: 27, which: 27 });
  await waitFor(() =>
    expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull(),
  );
  await waitFor(() => expect(document.activeElement).toBe(trigger));
});

test('日志页只提供现有只读操作，默认每页20条且支持全部约定数量', async () => {
  const fetcher = mount([first], 201);
  await screen.findByText(/^共 201 条操作记录/);
  expect(lastQuery(fetcher).get('page_size')).toBe('20');
  expect(screen.queryByRole('checkbox')).toBeNull();
  expect(
    screen.queryByRole('button', { name: /删除日志|清空日志|批量删除/ }),
  ).toBeNull();
  for (const size of [10, 50, 100, 20]) {
    fireEvent.click(screen.getByTitle('下一页'));
    await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
    const trigger = screen.getByRole('button', {
      name: '查看源码导入日志详情',
    });
    await waitFor(() => expect(trigger).toHaveProperty('disabled', false));
    fireEvent.click(trigger);
    await screen.findByRole('dialog', { name: '操作详情' });
    await changePageSize(size);
    await waitFor(() => {
      expect(lastQuery(fetcher).get('page')).toBe('1');
      expect(lastQuery(fetcher).get('page_size')).toBe(String(size));
      expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull();
    });
  }
});

test.each(['started_at', '-ended_at', 'ended_at', '-started_at'])(
  '排序%s保留原筛选并回到第一页、清除详情',
  async (ordering) => {
    const fetcher = mount([first], 41);
    await screen.findByText(/^共 41 条操作记录/);
    await valueFilter('操作类型', 'import');
    if (ordering === '-started_at') {
      fireEvent.change(screen.getByLabelText('日志排序'), {
        target: { value: 'ended_at' },
      });
      await waitFor(() =>
        expect(lastQuery(fetcher).get('ordering')).toBe('ended_at'),
      );
    }
    fireEvent.click(screen.getByTitle('下一页'));
    await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
    const trigger = screen.getByRole('button', {
      name: '查看源码导入日志详情',
    });
    await waitFor(() => expect(trigger).toHaveProperty('disabled', false));
    fireEvent.click(trigger);
    await screen.findByRole('dialog', { name: '操作详情' });
    fireEvent.change(screen.getByLabelText('日志排序'), {
      target: { value: ordering },
    });
    await waitFor(() => {
      expect(lastQuery(fetcher).get('page')).toBe('1');
      expect(lastQuery(fetcher).get('operation')).toBe('import');
      expect(lastQuery(fetcher).get('ordering')).toBe(
        ordering === '-started_at' ? null : ordering,
      );
      expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull();
    });
  },
);

test.each(['分页', '排序'])(
  '迟到%s结果不覆盖新排序，占位旧行不能打开详情且保留横向滚动位置',
  async (change) => {
    let resolveOld: ((response: Response) => void) | undefined;
    let oldSignal: AbortSignal | null | undefined;
    const fetcher = mount([first], 41, true, (query, options) => {
      const old =
        change === '分页'
          ? query.get('page') === '2'
          : query.get('ordering') === 'started_at';
      if (old) {
        oldSignal = options?.signal;
        return new Promise<Response>((resolve) => {
          resolveOld = resolve;
        });
      }
      return listResponse(
        [
          {
            ...first,
            object_name:
              query.get('ordering') === 'ended_at'
                ? '最新排序结果'
                : first.object_name,
          },
        ],
        41,
        query,
      );
    });
    await screen.findByText('示例源码');
    const table = screen.getByRole('region', { name: '操作日志表格区域' });
    table.scrollLeft = 120;
    if (change === '分页') fireEvent.click(screen.getByTitle('下一页'));
    else
      fireEvent.change(screen.getByLabelText('日志排序'), {
        target: { value: 'started_at' },
      });
    await waitFor(() => expect(oldSignal).toBeInstanceOf(AbortSignal));
    expect(screen.getByText('示例源码')).toBeTruthy();
    const trigger = screen.getByRole('button', {
      name: '查看源码导入日志详情',
    });
    expect(trigger).toHaveProperty('disabled', true);
    fireEvent.click(trigger);
    expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull();
    fireEvent.change(screen.getByLabelText('日志排序'), {
      target: { value: 'ended_at' },
    });
    await screen.findByText('最新排序结果');
    expect(lastQuery(fetcher).get('page')).toBe('1');
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => {
      resolveOld?.(listResponse([{ ...first, object_name: '迟到旧记录' }], 41));
    });
    expect(screen.queryByText('迟到旧记录')).toBeNull();
    expect(screen.getByText('最新排序结果')).toBeTruthy();
    expect(table.scrollLeft).toBe(120);
  },
);

test('日志总数变化令当前页不存在时回到第一页，不循环请求失效页', async () => {
  const fetcher = mount([first], 21, true, (query) =>
    query.get('page') === '2'
      ? apiFailure('PAGE_NOT_FOUND', '当前日志页不存在。', 404)
      : listResponse([first], 21, query),
  );
  await screen.findByText(/^共 21 条操作记录/);
  fireEvent.click(screen.getByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('1'));
  expect(
    fetcher.mock.calls.filter(
      ([path]) =>
        String(path).startsWith('/api/v1/operation-logs/?') &&
        String(path).includes('page=2'),
    ),
  ).toHaveLength(1);
  await screen.findByText('示例源码');
  expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull();
});

test('同一查询刷新保留详情，隐藏模块关闭抽屉并停止所有读取', async () => {
  const fetcher = mount();
  fireEvent.click(
    await screen.findByRole('button', { name: '查看源码导入日志详情' }),
  );
  await findLogDetails(41);
  const before = fetcher.mock.calls.length;
  await act(async () => {
    await fetcher.client.refetchQueries({
      queryKey: ['operation-logs'],
      type: 'active',
    });
  });
  expect(fetcher.mock.calls.length).toBeGreaterThan(before);
  expect(screen.getByRole('dialog', { name: '操作详情' })).toBeTruthy();
  expectLogDetails(41);
  fetcher.setActive(false);
  await waitFor(() =>
    expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull(),
  );
  const hiddenCalls = fetcher.mock.calls.length;
  await act(async () => {
    await fetcher.client.refetchQueries({
      queryKey: ['operation-logs'],
      type: 'active',
    });
  });
  expect(fetcher.mock.calls.length).toBe(hiddenCalls);
});

test('隐藏页面关闭四列表头筛选及内层日历，恢复时保留全部已应用条件且不抢焦点', async () => {
  const fetcher = mount([first], 201);
  render(<button>其他模块入口</button>);
  const otherModule = screen.getByRole('button', { name: '其他模块入口' });
  await screen.findByText(/^共 201 条操作记录/);
  await valueFilter('操作类型', 'import');
  await valueFilter('结果', 'succeeded');
  await timeFilter('开始时间', '2026-10-03T08:00:12', '');
  await timeFilter('结束时间', '', '2026-10-03T10:00:15');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('ended_before')).toBe(
      new Date('2026-10-03T10:00:15').toISOString(),
    ),
  );
  fireEvent.click(screen.getByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  const appliedQuery = Object.fromEntries(lastQuery(fetcher));
  for (const label of ['操作类型', '结果', '开始时间', '结束时间']) {
    fireEvent.click(screen.getByRole('button', { name: `${label}筛选` }));
    const dialog = await screen.findByRole('dialog', {
      name: `${label}筛选条件`,
    });
    if (label.includes('时间')) {
      fireEvent.click(within(dialog).getByLabelText(`${label}从`));
      await screen.findByRole('columnheader', { name: '日' });
    }
    otherModule.focus();
    fetcher.setActive(false);
    await waitFor(() => {
      expect(
        screen.queryByRole('dialog', { name: `${label}筛选条件` }),
      ).toBeNull();
      expect(screen.queryByRole('columnheader', { name: '日' })).toBeNull();
    });
    expect(document.activeElement).toBe(otherModule);
    const hiddenCalls = fetcher.mock.calls.length;
    await act(async () => {
      await fetcher.client.refetchQueries({
        queryKey: ['operation-logs'],
        type: 'active',
      });
    });
    expect(fetcher.mock.calls.length).toBe(hiddenCalls);
    fetcher.setActive(true);
    await screen.findByText(/^共 201 条操作记录/);
    expect(Object.fromEntries(lastQuery(fetcher))).toEqual(appliedQuery);
    expect(document.activeElement).toBe(otherModule);
    const trigger = screen.getByRole('button', { name: `${label}筛选` });
    expect(trigger.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(trigger);
    const restored = await screen.findByRole('dialog', {
      name: `${label}筛选条件`,
    });
    if (label === '操作类型' || label === '结果') {
      expect(within(restored).getByLabelText(`${label}条件`)).toHaveProperty(
        'value',
        label === '操作类型' ? 'import' : 'succeeded',
      );
    } else {
      expect(
        within(restored).getByLabelText(
          `${label}${label === '开始时间' ? '从' : '至'}`,
        ),
      ).toHaveProperty(
        'value',
        label === '开始时间' ? '2026-10-03 08:00:12' : '2026-10-03 10:00:15',
      );
    }
    fireEvent.keyDown(restored, { key: 'Escape' });
    await waitFor(() =>
      expect(trigger.getAttribute('aria-expanded')).toBe('false'),
    );
  }
});

test('隐藏页面关闭页容量下拉，恢复保留页码与数量且不聚焦隐藏入口', async () => {
  const fetcher = mount([first], 201);
  render(<button>其他模块入口</button>);
  const otherModule = screen.getByRole('button', { name: '其他模块入口' });
  await screen.findByText(/^共 201 条操作记录/);
  await changePageSize(50);
  await waitFor(() => expect(lastQuery(fetcher).get('page_size')).toBe('50'));
  fireEvent.click(screen.getByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  fireEvent.mouseDown(screen.getByRole('combobox', { name: '每页日志数量' }));
  await screen.findByRole('option', { name: /^50(?:\s|$)/ });
  otherModule.focus();
  fetcher.setActive(false);
  await waitFor(() => expect(screen.queryByRole('listbox')).toBeNull());
  expect(document.activeElement).toBe(otherModule);
  const hiddenCalls = fetcher.mock.calls.length;
  await act(async () => {
    await fetcher.client.refetchQueries({
      queryKey: ['operation-logs'],
      type: 'active',
    });
  });
  expect(fetcher.mock.calls.length).toBe(hiddenCalls);
  fetcher.setActive(true);
  await screen.findByText(/^共 201 条操作记录/);
  expect(lastQuery(fetcher).get('page')).toBe('2');
  expect(lastQuery(fetcher).get('page_size')).toBe('50');
  expect(document.activeElement).toBe(otherModule);
  const control = screen.getByRole('combobox', { name: '每页日志数量' });
  fireEvent.mouseDown(control);
  const selected = await screen.findByRole('option', { name: /^50(?:\s|$)/ });
  expect(selected.getAttribute('aria-selected')).toBe('true');
  fireEvent.keyDown(control, { key: 'Escape', keyCode: 27, which: 27 });
});

test('三秒轮询重新读取当前查询时保留已打开的同一条详情', async () => {
  vi.useFakeTimers();
  const fetcher = mount();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(50);
  });
  fireEvent.click(screen.getByRole('button', { name: '查看源码导入日志详情' }));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(500);
  });
  expect(screen.getByRole('dialog', { name: '操作详情' })).toBeTruthy();
  expectLogDetails(41);
  const reads = () =>
    fetcher.mock.calls.filter(([path]) =>
      String(path).startsWith('/api/v1/operation-logs/?'),
    ).length;
  const before = reads();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3000);
  });
  expect(reads()).toBeGreaterThan(before);
  expect(screen.getByRole('dialog', { name: '操作详情' })).toBeTruthy();
  expectLogDetails(41);
});

test('列表读取失败明确显示原因，显式重试恢复真实记录', async () => {
  let attempts = 0;
  mount([first], 1, true, (query) => {
    attempts += 1;
    return attempts === 1
      ? apiFailure('LOGS_UNAVAILABLE', '操作日志暂时无法读取。')
      : listResponse([first], 1, query);
  });
  await screen.findByText('操作日志暂时无法读取。');
  expect(screen.queryByText('示例源码')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '重新查询' }));
  await screen.findByText('示例源码');
  expect(screen.queryByText('操作日志暂时无法读取。')).toBeNull();
});

test.each(['加载', '失败'])(
  '详情%s时关闭入口始终可用，关闭后恢复原按钮焦点并忽略迟到内容',
  async (state) => {
    let resolveDetail: ((response: Response) => void) | undefined;
    let detailSignal: AbortSignal | null | undefined;
    mount([first], 1, true, undefined, (path, options) => {
      if (path !== `/api/v1/operation-logs/${first.id}/`) return;
      detailSignal = options?.signal;
      return state === '失败'
        ? apiFailure('DETAIL_UNAVAILABLE', '详情暂不可读取。')
        : new Promise<Response>((resolve) => {
            resolveDetail = resolve;
          });
    });
    const trigger = await screen.findByRole('button', {
      name: '查看源码导入日志详情',
    });
    trigger.focus();
    fireEvent.click(trigger);
    const drawer = await screen.findByRole('dialog', { name: '操作详情' });
    await within(drawer).findByText(
      state === '失败' ? '详情暂不可读取。' : '正在读取操作详情…',
    );
    fireEvent.click(
      within(drawer).getByRole('button', { name: '关闭操作详情' }),
    );
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: '操作详情' })).toBeNull(),
    );
    await waitFor(() => expect(document.activeElement).toBe(trigger));
    if (state === '加载') expect(detailSignal?.aborted).toBe(true);
    await act(async () => {
      resolveDetail?.(new Response(JSON.stringify(first)));
    });
    expect(screen.queryByText('日志 ID')).toBeNull();
  },
);

test('导出同步重复点击只发出一次请求，取消及重新导出后正确恢复状态', async () => {
  const spies = downloadSpies();
  let resolveExport: ((response: Response) => void) | undefined;
  let exportSignal: AbortSignal | null | undefined;
  const fetcher = mount([first], 1, true, undefined, (path, options) => {
    if (!path.startsWith('/api/v1/operation-logs/export/')) return;
    exportSignal = options?.signal;
    return new Promise<Response>((resolve, reject) => {
      resolveExport = resolve;
      options?.signal?.addEventListener(
        'abort',
        () => reject(new DOMException('已取消', 'AbortError')),
        { once: true },
      );
    });
  });
  await screen.findByText(/^共 1 条操作记录/);
  const button = screen.getByRole('button', { name: '导出日志' });
  act(() => {
    button.click();
    button.click();
  });
  expect(
    fetcher.mock.calls.filter(([path]) => String(path).includes('/export/')),
  ).toHaveLength(1);
  const cancel = await screen.findByRole('button', { name: '取消导出' });
  fireEvent.click(cancel);
  await screen.findByText('已取消日志导出。');
  expect(exportSignal?.aborted).toBe(true);
  const retry = await screen.findByRole('button', { name: '导出日志' });
  expect(retry).toHaveProperty('disabled', false);
  fireEvent.click(retry);
  await waitFor(() =>
    expect(
      fetcher.mock.calls.filter(([path]) => String(path).includes('/export/')),
    ).toHaveLength(2),
  );
  await act(async () => {
    resolveExport?.(
      new Response('\ufeff日志编号,操作\r\n41,导入\r\n', {
        headers: { 'Content-Type': 'text/csv' },
      }),
    );
  });
  await screen.findByText('日志 CSV 已生成并开始下载。');
  expect(spies.click).toHaveBeenCalledOnce();
  expect(screen.getByRole('button', { name: '导出日志' })).toHaveProperty(
    'disabled',
    false,
  );
});

test('导出失败显示服务端原因并解除忙状态，下一次操作可成功', async () => {
  const spies = downloadSpies();
  let attempts = 0;
  mount([first], 1, true, undefined, (path) => {
    if (!path.startsWith('/api/v1/operation-logs/export/')) return;
    attempts += 1;
    return attempts === 1
      ? apiFailure(
          'EXPORT_LIMIT_EXCEEDED',
          '导出超过允许范围，请缩小筛选。',
          413,
        )
      : new Response('\ufeff日志编号,操作\r\n41,导入\r\n', {
          headers: { 'Content-Type': 'text/csv' },
        });
  });
  await screen.findByText(/^共 1 条操作记录/);
  fireEvent.click(screen.getByRole('button', { name: '导出日志' }));
  await screen.findByText('导出超过允许范围，请缩小筛选。');
  const button = screen.getByRole('button', { name: '导出日志' });
  expect(button).toHaveProperty('disabled', false);
  expect(spies.createObjectURL).not.toHaveBeenCalled();
  fireEvent.click(button);
  await screen.findByText('日志 CSV 已生成并开始下载。');
  expect(screen.queryByText('导出超过允许范围，请缩小筛选。')).toBeNull();
  expect(spies.click).toHaveBeenCalledOnce();
});

test('零匹配仍可导出现有契约的BOM表头CSV，不新增选择或删除能力', async () => {
  const spies = downloadSpies();
  const fetcher = mount([], 0, true, undefined, (path) =>
    path.startsWith('/api/v1/operation-logs/export/')
      ? new Response('\ufeff日志编号,操作\r\n', {
          headers: { 'Content-Type': 'text/csv' },
        })
      : undefined,
  );
  await screen.findByText('当前条件没有操作记录。');
  const button = screen.getByRole('button', { name: '导出日志' });
  expect(button).toHaveProperty('disabled', false);
  fireEvent.click(button);
  await screen.findByText('日志 CSV 已生成并开始下载。');
  expect(spies.click).toHaveBeenCalledOnce();
  expect(spies.createObjectURL).toHaveBeenCalledOnce();
  const blob = spies.createObjectURL.mock.calls[0]![0];
  expect(blob).toBeInstanceOf(Blob);
  const contents = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
  expect(contents).toContain('日志编号,操作');
  expect(
    fetcher.mock.calls.filter(([path]) => String(path).includes('/export/')),
  ).toHaveLength(1);
});

test('导出保留完整筛选且不带页码，下载后释放临时地址', async () => {
  const fetcher = mount([first], 21);
  const createObjectURL = vi.fn(() => 'blob:operation-export');
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURL,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: revokeObjectURL,
  });
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  await valueFilter('操作类型', 'import');
  await timeFilter('结束时间', '', '2026-10-03T10:00:12');
  await waitFor(() =>
    expect(lastQuery(fetcher).get('ended_before')).toBe(
      new Date('2026-10-03T10:00:12').toISOString(),
    ),
  );
  fireEvent.click(await screen.findByTitle('下一页'));
  await waitFor(() => expect(lastQuery(fetcher).get('page')).toBe('2'));
  fireEvent.click(screen.getByRole('button', { name: '导出日志' }));
  await waitFor(() => expect(click).toHaveBeenCalledOnce());
  const path = fetcher.mock.calls
    .map(([value]) => String(value))
    .find((value) => value.includes('/export/'))!;
  expect(
    Object.fromEntries(new URL(path, 'http://localhost').searchParams),
  ).toEqual({
    operation: 'import',
    ended_before: new Date('2026-10-03T10:00:12').toISOString(),
  });
  expect(createObjectURL).toHaveBeenCalledOnce();
  await waitFor(
    () => expect(revokeObjectURL).toHaveBeenCalledWith('blob:operation-export'),
    { timeout: 2000 },
  );
});
