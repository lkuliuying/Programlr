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
import type { Job } from '../../shared/api/generated/schema';

const target: Job = {
  id: '00000000-0000-0000-0000-000000000001',
  kind: 'system_check',
  status: 'succeeded',
  snapshot_id: null,
  previous_job_id: null,
  parent_job_id: null,
  source_kind: '',
  result_deleted_at: null,
  result_deleted: false,
  result_url: '/api/v1/system-checks/00000000-0000-0000-0000-000000000001/',
  stage: 'completed',
  progress: null,
  error: null,
  created_at: '2026-10-03T00:00:00Z',
  updated_at: '2026-10-03T00:00:00Z',
};
const listed: Job = {
  ...target,
  id: '00000000-0000-0000-0000-000000000002',
  result_url: '/api/v1/system-checks/00000000-0000-0000-0000-000000000002/',
  created_at: '2026-10-02T00:00:00Z',
};
const clients: QueryClient[] = [];
afterEach(() => {
  cleanup();
  clients.forEach((client) => client.clear());
  clients.length = 0;
  vi.unstubAllGlobals();
  window.history.replaceState({}, '', '/');
});
const response = (value: unknown) => new Response(JSON.stringify(value));
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  const element = (selectedJobId = target.id) => (
    <QueryClientProvider client={client}>
      <JobsPage selectedJobId={selectedJobId} />
    </QueryClientProvider>
  );
  return { ...render(element()), element };
}

test('通知指定任务不在当前批次时独立读取，迟到加载后定位可见技术详情', async () => {
  let finish: ((response: Response) => void) | undefined;
  const fetcher = vi.fn((path: string) =>
    path === `/api/v1/jobs/${target.id}/`
      ? new Promise<Response>((resolve) => {
          finish = resolve;
        })
      : Promise.resolve(
          response({ count: 1, previous: null, next: null, results: [listed] }),
        ),
  );
  vi.stubGlobal('fetch', fetcher);
  mount();
  await waitFor(() => expect(finish).toBeDefined());
  await act(async () => finish?.(response(target)));
  await screen.findByText(target.id);
  const summary = screen.getByText('任务技术详情');
  await waitFor(() => expect(document.activeElement).toBe(summary));
  expect(summary.closest('details')).toHaveProperty('open', true);
  expect(
    fetcher.mock.calls.some(([path]) => path === `/api/v1/jobs/${target.id}/`),
  ).toBe(true);
});

test('指定任务从A切换到B后取消A详情，迟到的旧响应不能覆盖当前选择', async () => {
  let finish: ((response: Response) => void) | undefined;
  let signal: AbortSignal | undefined;
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string, options: RequestInit) => {
      if (path === `/api/v1/jobs/${target.id}/`) {
        signal = options.signal as AbortSignal;
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      }
      return Promise.resolve(
        response({ count: 1, previous: null, next: null, results: [listed] }),
      );
    }),
  );
  const { rerender, element } = mount();
  await waitFor(() => expect(signal).toBeDefined());
  await screen.findByRole('button', { name: /^查看任务详情：/ });
  rerender(element(listed.id));
  await screen.findByText(listed.id);
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => finish?.(response(target)));
  expect(screen.queryByText(target.id)).toBeNull();
  expect(screen.getByText(listed.id)).toBeTruthy();
});

test('通知任务载入后点击当前批次另一条记录，可以切换详情且不会重新读取通知目标', async () => {
  const fetcher = vi.fn(async (path: string) =>
    path === `/api/v1/jobs/${target.id}/`
      ? response(target)
      : response({ count: 1, previous: null, next: null, results: [listed] }),
  );
  vi.stubGlobal('fetch', fetcher);
  mount();
  await screen.findByText(target.id);
  fireEvent.click(screen.getByRole('button', { name: /^查看任务详情：/ }));
  await screen.findByText(listed.id);
  expect(screen.queryByText(target.id)).toBeNull();
  expect(document.activeElement).toBe(screen.getByText('任务技术详情'));
  expect(
    fetcher.mock.calls.filter(
      ([path]) => path === `/api/v1/jobs/${target.id}/`,
    ),
  ).toHaveLength(1);
});
