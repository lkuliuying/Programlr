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

const time = '2026-10-03T00:00:00Z';
const snapshot = '00000000-0000-0000-0000-000000000002';
const analysis = '00000000-0000-0000-0000-000000000003';
const otherAnalysis = '00000000-0000-0000-0000-000000000004';
const clients: QueryClient[] = [];
afterEach(() => {
  cleanup();
  clients.forEach((client) => client.clear());
  clients.length = 0;
  vi.unstubAllGlobals();
});
const page = (results: unknown[] = []) =>
  new Response(
    JSON.stringify({
      count: results.length,
      previous: null,
      next: null,
      results,
    }),
  );
function mount() {
  const props = {
    snapshotId: snapshot,
    analysisId: analysis,
    files: [],
    onProject: vi.fn(),
    onFile: vi.fn(),
    onEndpoint: vi.fn(),
  };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  clients.push(client);
  const element = (data = props) => (
    <QueryClientProvider client={client}>
      <WorkspaceSearch {...data} />
    </QueryClientProvider>
  );
  return { ...render(element()), props, element };
}

test('关闭搜索取消执行中的 GET，迟到响应不能恢复旧结果或导航', async () => {
  const signals: AbortSignal[] = [];
  const resolutions: Array<(response: Response) => void> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn((_path: string, options: RequestInit) => {
      signals.push(options.signal as AbortSignal);
      return new Promise<Response>((resolve) => resolutions.push(resolve));
    }),
  );
  const { props } = mount();
  fireEvent.change(screen.getByRole('textbox'), {
    target: { value: '旧项目' },
  });
  await waitFor(() => expect(signals).toHaveLength(2));
  fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Escape' });
  await waitFor(() =>
    expect(signals.every((signal) => signal.aborted)).toBe(true),
  );
  await act(async () => resolutions.forEach((resolve) => resolve(page())));
  expect(props.onProject).not.toHaveBeenCalled();
  expect(props.onEndpoint).not.toHaveBeenCalled();
  expect(
    screen.queryByRole('region', { name: '搜索本地项目与当前上下文' }),
  ).toBeNull();
  expect(screen.getByRole('textbox')).toHaveProperty('value', '旧项目');
});

test.each(['', ' \t\u3000 '])(
  '清空或改为纯空白立即隐藏并取消查询，迟到响应不能重新展开：%j',
  async (value) => {
    const signals: AbortSignal[] = [];
    const resolutions: Array<(response: Response) => void> = [];
    const fetcher = vi.fn((_path: string, options: RequestInit) => {
      signals.push(options.signal as AbortSignal);
      return new Promise<Response>((resolve) => resolutions.push(resolve));
    });
    vi.stubGlobal('fetch', fetcher);
    const { props } = mount();
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '旧项目' } });
    await waitFor(() => expect(signals).toHaveLength(2));
    expect(
      screen.getByRole('region', { name: '搜索本地项目与当前上下文' }),
    ).toBeTruthy();
    fireEvent.change(input, { target: { value } });
    expect(
      screen.queryByRole('region', { name: '搜索本地项目与当前上下文' }),
    ).toBeNull();
    expect(input.getAttribute('aria-expanded')).toBe('false');
    await waitFor(() =>
      expect(signals.every((signal) => signal.aborted)).toBe(true),
    );
    await act(async () => resolutions.forEach((resolve) => resolve(page())));
    expect(
      screen.queryByRole('region', { name: '搜索本地项目与当前上下文' }),
    ).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(props.onProject).not.toHaveBeenCalled();
    expect(props.onEndpoint).not.toHaveBeenCalled();
  },
);

test('关键词变化取消旧查询，忽略无视取消的迟到响应', async () => {
  const signals: AbortSignal[] = [];
  const old: Array<(response: Response) => void> = [];
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string, options: RequestInit) => {
      const url = new URL(path, 'http://local.test');
      expect(options.method).toBeUndefined();
      if (url.searchParams.get('q') === '旧项目') {
        signals.push(options.signal as AbortSignal);
        return new Promise<Response>((resolve) => old.push(resolve));
      }
      return Promise.resolve(
        page(
          url.pathname === '/api/v1/projects/'
            ? [
                {
                  id: '00000000-0000-0000-0000-000000000001',
                  name: '新项目结果',
                  created_at: time,
                },
              ]
            : [],
        ),
      );
    }),
  );
  mount();
  const input = screen.getByRole('textbox');
  fireEvent.change(input, { target: { value: '旧项目' } });
  await waitFor(() => expect(signals).toHaveLength(2));
  fireEvent.change(input, { target: { value: '新项目' } });
  expect(
    screen.queryByRole('region', { name: '搜索本地项目与当前上下文' }),
  ).toBeNull();
  await screen.findByRole('button', { name: '新项目结果' });
  expect(signals.every((signal) => signal.aborted)).toBe(true);
  await act(async () => old.forEach((resolve) => resolve(page())));
  expect(screen.getByRole('button', { name: '新项目结果' })).toBeTruthy();
});

test('切换分析上下文取消旧接口查询，不把旧结果带到新分析', async () => {
  let signal: AbortSignal | undefined;
  let finish: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string, options: RequestInit) => {
      if (path.startsWith(`/api/v1/analyses/${analysis}/`)) {
        signal = options.signal as AbortSignal;
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      }
      return Promise.resolve(page());
    }),
  );
  const { rerender, props, element } = mount();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'GET' } });
  await waitFor(() => expect(signal).toBeDefined());
  rerender(element({ ...props, analysisId: otherAnalysis }));
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => finish?.(page()));
  expect(props.onEndpoint).not.toHaveBeenCalled();
  expect(screen.getByRole('textbox')).toHaveProperty('value', 'GET');
});
