import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TaskBoard } from './TaskBoard';

const task = {
  id: '12345678-1234-4234-8234-123456789abc',
  title: '阅读源码',
  created_at: '2026-09-29T00:00:00Z',
};
const empty = { count: 0, next: null, previous: null, results: [] };
const json = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });
function show() {
  // jsdom 不实现尺寸观测；这里只补浏览器 API，不替代业务请求断言。
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  );
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false, gcTime: 0 },
            mutations: { retry: false },
          },
        })
      }
    >
      <TaskBoard />
    </QueryClientProvider>,
  );
}
function input(title: string) {
  fireEvent.change(screen.getByLabelText('任务标题'), {
    target: { value: title },
  });
}
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test('成功提交后更新列表，重新挂载仍读取已保存任务', async () => {
  let saved = false;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/'))
        return json({ csrf_token: 'test-only-token' });
      if (options.method === 'POST') {
        saved = true;
        expect(JSON.parse(String(options.body))).toEqual({ title: '阅读源码' });
        return json(task, 201);
      }
      return json(saved ? { ...empty, count: 1, results: [task] } : empty);
    }),
  );
  const view = show();
  expect(await screen.findByText('一页新的开始')).toBeTruthy();
  input('阅读源码');
  fireEvent.click(screen.getByRole('button', { name: '创建任务' }));
  expect(await screen.findByText('任务已保存。')).toBeTruthy();
  expect(await screen.findByRole('heading', { name: '阅读源码' })).toBeTruthy();
  view.unmount();
  show();
  expect(await screen.findByRole('heading', { name: '阅读源码' })).toBeTruthy();
  expect(sessionStorage.length).toBe(0);
});

test.each(['', '  \t ', 'x'.repeat(201)])(
  '本地拒绝非法标题 %#，不发送写请求',
  async (title) => {
    const fetcher = vi.fn(async () => json(empty));
    vi.stubGlobal('fetch', fetcher);
    show();
    await screen.findByText('一页新的开始');
    input(title);
    fireEvent.click(screen.getByRole('button', { name: '创建任务' }));
    expect(
      await screen.findByText('请输入 1–200 个字符的标题，不能只有空白。'),
    ).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
  },
);

test('未知结果不自动重发，重新挂载后沿用原键和原标题恢复', async () => {
  const keys: string[] = [];
  const bodies: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/'))
        return json({ csrf_token: 'test-only-token' });
      if (options.method === 'POST') {
        keys.push(new Headers(options.headers).get('Idempotency-Key') ?? '');
        bodies.push(String(options.body));
        if (keys.length === 1) throw new TypeError('network');
        return json(task);
      }
      return json(empty);
    }),
  );
  const view = show();
  input('阅读源码');
  fireEvent.click(screen.getByRole('button', { name: '创建任务' }));
  await screen.findByText(
    '连接未完成。若已提交，请使用原操作恢复，避免重复创建。',
  );
  expect(keys).toHaveLength(1);
  view.unmount();
  show();
  input('阅读源码');
  fireEvent.click(screen.getByRole('button', { name: '恢复这次提交' }));
  await screen.findByText('任务已保存。');
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  expect(bodies[0]).toBe(bodies[1]);
});

test('显示服务端字段错误并允许修正', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/'))
        return json({ csrf_token: 'test-only-token' });
      if (options.method === 'POST')
        return json(
          {
            code: 'VALIDATION_ERROR',
            message: '参数错误。',
            details: { fields: { title: ['服务端拒绝标题。'] } },
            request_id: 'request-example',
          },
          400,
        );
      return json(empty);
    }),
  );
  show();
  input('阅读源码');
  fireEvent.click(screen.getByRole('button', { name: '创建任务' }));
  await screen.findByText('服务端拒绝标题。');
  await waitFor(() =>
    expect(screen.getByRole('button', { name: '创建任务' })).toBeTruthy(),
  );
  expect(sessionStorage.length).toBe(0);
});

test('创建成功但列表失败时保留真实成功信息', async () => {
  let saved = false;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/'))
        return json({ csrf_token: 'test-only-token' });
      if (options.method === 'POST') {
        saved = true;
        return json(task, 201);
      }
      if (saved) throw new TypeError('network');
      return json(empty);
    }),
  );
  show();
  input('阅读源码');
  fireEvent.click(screen.getByRole('button', { name: '创建任务' }));
  await screen.findByText('任务已保存。');
  expect(
    await screen.findByText('任务已创建，但列表暂时未能刷新。'),
  ).toBeTruthy();
});

test.each([400, 409])(
  '恢复遇到 %s 时保留原键并允许重新填写原标题',
  async (status) => {
    const key = '12345678-1234-4234-8234-123456789abc';
    sessionStorage.setItem('task-board.pending-key.v1', key);
    const keys: string[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (path: string, options: RequestInit) => {
        if (path.endsWith('/csrf/'))
          return json({ csrf_token: 'test-only-token' });
        if (options.method === 'POST') {
          keys.push(new Headers(options.headers).get('Idempotency-Key') ?? '');
          return keys.length === 1
            ? json(
                {
                  code: 'RECOVERY_REJECTED',
                  message: '请核对原标题。',
                  details: {},
                  request_id: 'request-example',
                },
                status,
              )
            : json(task);
        }
        return json(empty);
      }),
    );
    show();
    input('填错的标题');
    fireEvent.click(screen.getByRole('button', { name: '恢复这次提交' }));
    await screen.findByText('请核对原标题。 请求标识：request-example');
    expect(sessionStorage.getItem('task-board.pending-key.v1')).toBe(key);
    expect(
      (screen.getByLabelText('任务标题') as HTMLTextAreaElement).disabled,
    ).toBe(false);
    input('阅读源码');
    fireEvent.click(screen.getByRole('button', { name: '恢复这次提交' }));
    await screen.findByText('任务已保存。');
    expect(keys).toEqual([key, key]);
  },
);
