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
import { JobsPage } from './JobsPage';
import { SystemStatusPage } from './SystemStatusPage';
import type { Job } from '../../shared/api/generated/schema';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  window.history.replaceState({}, '', '/');
  vi.unstubAllGlobals();
});

test('记录翻页保留项目和快照，并能通过浏览器历史返回', async () => {
  const project = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const snapshot = 'ad8df4d4-d2c7-4c58-886d-8f0084f29652';
  window.history.replaceState(
    {},
    '',
    `?project=${project}&snapshot=${snapshot}&section=jobs`,
  );
  const fetcher = vi.fn(
    async (path: string) =>
      new Response(
        JSON.stringify({
          count: 21,
          results: [],
          previous: path.includes('page=2&')
            ? '/api/v1/jobs/?page=1&page_size=20'
            : null,
          next: path.includes('page=2&')
            ? null
            : '/api/v1/jobs/?page=2&page_size=20',
        }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  show();
  fireEvent.click(await screen.findByRole('button', { name: '下一批记录' }));
  await screen.findByText('第 2 批 · 每批最多 20 条');
  expect(new URLSearchParams(window.location.search).get('project')).toBe(
    project,
  );
  expect(new URLSearchParams(window.location.search).get('snapshot')).toBe(
    snapshot,
  );
  expect(
    fetcher.mock.calls.some(
      ([path]) => path === '/api/v1/jobs/?page=2&page_size=20',
    ),
  ).toBe(true);
  act(() => window.history.back());
  await screen.findByText('第 1 批 · 每批最多 20 条');
});

test('旧任务历史链接继续读取指定批次，系统检查不混入任务历史', async () => {
  window.history.replaceState({}, '', '?view=jobs&page=2');
  const fetcher = vi.fn<typeof fetch>(
    async () =>
      new Response(
        JSON.stringify({ count: 0, results: [], next: null, previous: null }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  show();
  await screen.findByText('第 2 批 · 每批最多 20 条');
  expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/jobs/?page=2&page_size=20');
  expect(screen.queryByRole('button', { name: '开始基础检查' })).toBeNull();
});
function show(
  system = false,
  props: { active?: boolean; onCheck?: (url: string) => void } = {},
) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      {system ? (
        <SystemStatusPage onHistory={vi.fn()} />
      ) : (
        <JobsPage {...props} />
      )}
    </QueryClientProvider>,
  );
}
test('无任务时呈现真实空状态', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
        ),
      ),
  );
  show();
  expect(
    await screen.findByText(
      '还没有任务。可在系统状态开始基础检查，或在项目导入中导入源码。',
    ),
  ).toBeTruthy();
  expect(screen.queryByRole('button', { name: '开始基础检查' })).toBeNull();
});
test('未知提交结果在重新挂载后用原键恢复', async () => {
  const keys: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/'))
        return new Response(
          JSON.stringify({ csrf_token: 'synthetic-test-token' }),
        );
      if (options.method === 'POST') {
        keys.push(new Headers(options.headers).get('Idempotency-Key') ?? '');
        throw new TypeError('network');
      }
      return new Response(
        JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
      );
    }),
  );
  const view = show(true);
  fireEvent.click(screen.getByRole('button', { name: '开始基础检查' }));
  await waitFor(() => expect(keys).toHaveLength(1));
  view.unmount();
  show(true);
  fireEvent.click(screen.getByRole('button', { name: '恢复这次提交' }));
  await waitFor(() => expect(keys).toHaveLength(2));
  expect(keys[0]).toBe(keys[1]);
});

test('导入历史显示快照且不误取基础检查结果', async () => {
  const snapshot = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const fetcher = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'import-job',
            kind: 'import',
            status: 'succeeded',
            stage: 'completed',
            snapshot_id: snapshot,
            previous_job_id: null,
            parent_job_id: null,
            source_kind: '',
            result_deleted_at: null,
            result_deleted: false,
            progress: null,
            error: null,
            result_url: `/api/v1/snapshots/${snapshot}/`,
            created_at: '2026-09-29T00:00:00Z',
            updated_at: '2026-09-29T00:00:00Z',
          },
        ],
      }),
    ),
  );
  vi.stubGlobal('fetch', fetcher);
  show();
  expect(await screen.findByText('项目导入')).toBeTruthy();
  fireEvent.click(
    screen.getByRole('button', { name: /查看任务详情：项目导入/ }),
  );
  expect(screen.getByText(snapshot)).toBeTruthy();
  expect(screen.queryByRole('button', { name: '查看检查结果' })).toBeNull();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('分析历史绑定原快照且不触发基础检查结果请求', async () => {
  const snapshot = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const fetcher = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'analysis-job',
            kind: 'analysis',
            status: 'succeeded',
            stage: 'completed',
            snapshot_id: snapshot,
            previous_job_id: null,
            parent_job_id: null,
            source_kind: '',
            result_deleted_at: null,
            result_deleted: false,
            progress: null,
            error: null,
            result_url: `/api/v1/analyses/${snapshot}/`,
            created_at: '2026-09-29T00:00:00Z',
            updated_at: '2026-09-29T00:00:00Z',
          },
        ],
      }),
    ),
  );
  vi.stubGlobal('fetch', fetcher);
  show();
  expect(await screen.findByText('源码分析')).toBeTruthy();
  fireEvent.click(
    screen.getByRole('button', { name: /查看任务详情：源码分析/ }),
  );
  expect(screen.getByText(snapshot)).toBeTruthy();
  expect(screen.queryByRole('button', { name: '查看检查结果' })).toBeNull();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('重试记录重新挂载后仍显示原任务且不自动提交', async () => {
  const previous = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const fetcher = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'retry-job',
              kind: 'system_check',
              status: 'failed',
              stage: 'failed',
              snapshot_id: null,
              previous_job_id: previous,
              progress: null,
              result_url: null,
              error: {
                code: 'QUEUE_TIMEOUT',
                message: '排队超时',
                request_id: 'test',
                details: {},
              },
              created_at: '2026-09-29T00:00:00Z',
              updated_at: '2026-09-29T00:00:00Z',
            },
          ],
        }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  const view = show();
  fireEvent.click(
    await screen.findByRole('button', { name: /查看任务详情：基础链路检查/ }),
  );
  expect(await screen.findByText(previous)).toBeTruthy();
  expect(screen.getByText('重试自任务：')).toBeTruthy();
  view.unmount();
  show();
  fireEvent.click(
    await screen.findByRole('button', { name: /查看任务详情：基础链路检查/ }),
  );
  expect(await screen.findByText(previous)).toBeTruthy();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

function historyJob(overrides: Partial<Job> = {}): Job {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    kind: 'system_check',
    status: 'failed',
    stage: 'failed',
    snapshot_id: null,
    previous_job_id: null,
    parent_job_id: null,
    source_kind: '',
    result_deleted_at: null,
    result_deleted: false,
    progress: null,
    result_url: null,
    error: {
      code: 'QUEUE_TIMEOUT',
      message: '排队超时',
      request_id: 'synthetic-detail-trace',
      details: { reason: 'synthetic-failure' },
    },
    created_at: '2026-10-03T00:00:00Z',
    updated_at: '2026-10-03T00:01:00Z',
    ...overrides,
  };
}

test('任务详情显式选择、单实例折叠并保留完整错误与重试关系，不额外读取或提交', async () => {
  const previous = '00000000-0000-0000-0000-000000000003';
  const first = historyJob({ previous_job_id: previous });
  const second = historyJob({
    id: '00000000-0000-0000-0000-000000000002',
    created_at: '2026-10-03T02:00:00Z',
    error: null,
  });
  const fetcher = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          count: 2,
          next: null,
          previous: null,
          results: [first, second],
        }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  show();
  const buttons = await screen.findAllByRole('button', {
    name: /查看任务详情：/,
  });
  expect(screen.queryByText(first.id)).toBeNull();
  expect(document.querySelector('details')).toBeNull();
  fireEvent.click(buttons[0]);
  expect(screen.getByText(first.id)).toBeTruthy();
  expect(screen.getByText(previous)).toBeTruthy();
  expect(screen.getByText('QUEUE_TIMEOUT')).toBeTruthy();
  expect(screen.getByText('synthetic-detail-trace')).toBeTruthy();
  expect(screen.getByText('{"reason":"synthetic-failure"}')).toBeTruthy();
  expect(screen.getByText('未提供处理量')).toBeTruthy();
  // 详情渲染后通过 RAF 聚焦，保留原焦点断言并等待该浏览器调度完成。
  await waitFor(() =>
    expect(document.activeElement).toBe(screen.getByText('任务技术详情')),
  );
  const details = document.querySelector('details')!;
  expect(details.open).toBe(true);
  details.open = false;
  fireEvent(details, new Event('toggle', { bubbles: true }));
  expect(buttons[0].getAttribute('aria-expanded')).toBe('false');
  fireEvent.click(buttons[1]);
  expect(document.querySelectorAll('details')).toHaveLength(1);
  expect(document.querySelector('details')!.open).toBe(true);
  expect(screen.getByText(second.id)).toBeTruthy();
  expect(screen.queryByText(first.id)).toBeNull();
  expect(screen.queryByText(previous)).toBeNull();
  expect(fetcher).toHaveBeenCalledTimes(1);
});

test('历史结果入口沿用检查结果跳转，不在历史页查询检查或执行新任务', async () => {
  const result = '/api/v1/system-checks/00000000-0000-0000-0000-000000000004/';
  const fetcher = vi.fn<typeof fetch>(
    async () =>
      new Response(
        JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [
            historyJob({
              status: 'succeeded',
              stage: 'completed',
              result_url: result,
              error: null,
            }),
          ],
        }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  const onCheck = vi.fn();
  show(false, { onCheck });
  fireEvent.click(await screen.findByRole('button', { name: '查看检查结果' }));
  expect(onCheck).toHaveBeenCalledWith(result);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/jobs/?page=1&page_size=20');
});

test('未激活历史页不查询，未加载状态不冒充零条或成功记录', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  show(false, { active: false });
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.getByRole('heading', { name: '执行记录 —' })).toBeTruthy();
  expect(screen.queryByText('已完成')).toBeNull();
  expect(screen.queryByText(/还没有任务/)).toBeNull();
});
