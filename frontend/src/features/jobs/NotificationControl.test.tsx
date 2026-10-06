import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotificationControl } from './NotificationControl';
const id = '00000000-0000-0000-0000-000000000001';
const time = '2026-10-03T00:00:00Z';
const job = {
  id,
  kind: 'system_check',
  snapshot_id: null,
  previous_job_id: null,
  status: 'succeeded',
  stage: 'completed',
  progress: null,
  result_url: `/api/v1/system-checks/${id}/`,
  error: null,
  created_at: time,
  updated_at: time,
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function mount(onTask = vi.fn()) {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value() {
      this.setAttribute('open', '');
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value() {
      this.removeAttribute('open');
    },
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    ...render(
      <QueryClientProvider client={client}>
        <NotificationControl onTask={onTask} />
      </QueryClientProvider>,
    ),
    onTask,
  };
}
test('历史未读、打开及查看都不写；显式已读才PATCH并刷新计数', async () => {
  let read = false;
  const writes: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path === '/api/v1/csrf/')
        return new Response(JSON.stringify({ csrf_token: 'synthetic' }));
      if (options.method === 'PATCH') {
        writes.push(path);
        read = true;
        expect(JSON.parse(String(options.body))).toEqual({ read: true });
        return new Response(JSON.stringify({ job, read }));
      }
      return new Response(
        JSON.stringify({
          count: 1,
          previous: null,
          next: null,
          results: [{ job, read }],
          unread_count: read ? 0 : 1,
          as_of: time,
          read_through: null,
        }),
      );
    }),
  );
  const { onTask } = mount();
  fireEvent.click(
    await screen.findByRole('button', { name: '任务通知，1 条未读' }),
  );
  expect(writes).toEqual([]);
  fireEvent.click(screen.getByRole('button', { name: '查看任务' }));
  expect(onTask).toHaveBeenCalledWith(id);
  expect(writes).toEqual([]);
  fireEvent.click(screen.getByRole('button', { name: '任务通知，1 条未读' }));
  fireEvent.click(screen.getByRole('button', { name: '标记已读' }));
  await screen.findByRole('button', { name: '任务通知，0 条未读' });
  expect(writes).toEqual([`/api/v1/notifications/${id}/`]);
});
test('全部已读使用列表as_of；未知写入只读取核实，不自动重试', async () => {
  let through: string | null = null;
  let patches = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path === '/api/v1/csrf/')
        return new Response(JSON.stringify({ csrf_token: 'synthetic' }));
      if (options.method === 'PATCH') {
        patches++;
        expect(path).toBe('/api/v1/notification-read-state/');
        expect(JSON.parse(String(options.body))).toEqual({
          read_through: time,
        });
        through = time;
        throw new Error('合成网络断开');
      }
      return new Response(
        JSON.stringify({
          count: 1,
          previous: null,
          next: null,
          results: [{ job, read: !!through }],
          unread_count: through ? 0 : 1,
          as_of: time,
          read_through: through,
        }),
      );
    }),
  );
  mount();
  fireEvent.click(
    await screen.findByRole('button', { name: '任务通知，1 条未读' }),
  );
  fireEvent.click(screen.getByRole('button', { name: '全部标记已读' }));
  await waitFor(() =>
    expect(screen.getByRole('status').textContent).toContain('已核实'),
  );
  expect(patches).toBe(1);
});
