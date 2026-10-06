import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from '@tanstack/react-query';
import type { Snapshot } from '../../shared/api/generated/schema';
import { SnapshotNameForm } from './SnapshotNameForm';
import {
  getSnapshot,
  listSnapshots,
  parseSnapshot,
  renameSnapshot,
} from './api/projects-api';

const id = (n: number) =>
  `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
const snapshot: Snapshot = {
  id: id(2),
  project_id: id(1),
  job_id: id(3),
  name: '',
  created_at: '2026-10-01T00:00:00Z',
  source_extensions: ['.py'],
  source_manifest_names: [],
  preparation_status: 'pending',
  source_scan_id: null,
  scan_job_id: null,
  analysis_job_id: null,
  analysis_id: null,
  summary: {
    entries: 9,
    accepted: 9,
    excluded: 0,
    skipped: 0,
    rejected: 0,
    declared_bytes: 1,
    extracted_bytes: 1,
    reasons: {},
  },
};

function setup(fail = false) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const page = { count: 1, next: null, previous: null, results: [snapshot] };
  cache.setQueryData(
    ['projects', 'snapshot', snapshot.project_id, snapshot.id],
    snapshot,
  );
  cache.setQueryData(['projects', 'snapshots', snapshot.project_id, 1], page);
  cache.setQueryData(['projects', 'snapshots', snapshot.project_id, 2], page);
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/')
      return new Response(JSON.stringify({ csrf_token: 'test-csrf' }));
    if (fail)
      return new Response(
        JSON.stringify({
          code: 'SERVICE_UNAVAILABLE',
          message: '暂时无法保存名称。',
          request_id: 'test-request',
          details: {},
        }),
        { status: 503 },
      );
    const body = JSON.parse(options.body as string) as { name: string };
    return new Response(JSON.stringify({ ...snapshot, name: body.name }));
  });
  vi.stubGlobal('fetch', fetcher);
  const view = (hidden: boolean) => (
    <QueryClientProvider client={cache}>
      <div hidden={hidden}>
        <SnapshotNameForm snapshot={snapshot} />
      </div>
    </QueryClientProvider>
  );
  const rendered = render(view(false));
  return { cache, fetcher, rendered, view };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('仅显式保存名称，隐藏切页保留草稿，保存后更新所有分页及详情缓存', async () => {
  const { cache, fetcher, rendered, view } = setup();
  expect(screen.queryByRole('textbox', { name: '快照名称' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  const input = screen.getByRole('textbox', { name: '快照名称' });
  fireEvent.change(input, { target: { value: ' 创建任务基线 ' } });
  fireEvent.click(screen.getByRole('button', { name: '收起快照命名' }));
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  rendered.rerender(view(true));
  rendered.rerender(view(false));
  expect(screen.getByRole('textbox', { name: '快照名称' })).toHaveProperty(
    'value',
    ' 创建任务基线 ',
  );
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '保存快照名称' }));
  await screen.findByText('快照名称已保存。');
  const patch = fetcher.mock.calls.find(
    ([, options]) => options.method === 'PATCH',
  );
  expect(patch?.[0]).toBe(`/api/v1/snapshots/${snapshot.id}/`);
  expect(patch?.[1].body).toBe(JSON.stringify({ name: '创建任务基线' }));
  expect(patch?.[1].headers).toEqual({
    'Content-Type': 'application/json',
    'X-CSRFToken': 'test-csrf',
  });
  expect(
    cache.getQueryData([
      'projects',
      'snapshot',
      snapshot.project_id,
      snapshot.id,
    ]),
  ).toEqual({ ...snapshot, name: '创建任务基线' });
  for (const page of [1, 2])
    expect(
      cache.getQueryData(['projects', 'snapshots', snapshot.project_id, page]),
    ).toMatchObject({ results: [{ name: '创建任务基线' }] });
  expect(input).toHaveProperty('value', '创建任务基线');
});

test('保存失败保留草稿且不会自动重试或更新旧缓存', async () => {
  const { cache, fetcher } = setup(true);
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  const input = screen.getByRole('textbox', { name: '快照名称' });
  fireEvent.change(input, { target: { value: '待保存版本' } });
  fireEvent.click(screen.getByRole('button', { name: '保存快照名称' }));
  await screen.findByText('暂时无法保存名称。');
  expect(input).toHaveProperty('value', '待保存版本');
  expect(
    fetcher.mock.calls.filter(([, options]) => options.method === 'PATCH'),
  ).toHaveLength(1);
  expect(
    cache.getQueryData([
      'projects',
      'snapshot',
      snapshot.project_id,
      snapshot.id,
    ]),
  ).toEqual(snapshot);
  await waitFor(() => expect(input).not.toHaveProperty('disabled', true));
});

test('拒绝错误归属和缺失名称，旧空名响应仍正常解析', async () => {
  expect(parseSnapshot(snapshot)).toEqual(snapshot);
  expect(() => parseSnapshot({ ...snapshot, name: undefined })).toThrow(
    '响应结构或资源归属无效',
  );
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async (path: string) =>
        new Response(
          JSON.stringify(
            path === '/api/v1/csrf/'
              ? { csrf_token: 'test' }
              : { ...snapshot, project_id: id(99), name: '新名称' },
          ),
        ),
    ),
  );
  await expect(
    renameSnapshot(snapshot, '新名称', new AbortController().signal),
  ).rejects.toThrow('响应结构或资源归属无效');
});

test('空白、控制字符和超长名称不会发起写请求', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  for (const name of [' ', 'a\n', 'a\x85b', 'a'.repeat(201)])
    expect(() =>
      renameSnapshot(snapshot, name, new AbortController().signal),
    ).toThrow('快照名称须为');
  expect(fetcher).not.toHaveBeenCalled();
});

test('名称按Unicode字符计数，200个emoji可保存，201个emoji或BMP字符被拒绝且不写请求', async () => {
  const name = '😀'.repeat(200);
  expect(name.length).toBe(400);
  expect(parseSnapshot({ ...snapshot, name })).toEqual({ ...snapshot, name });
  const { fetcher, cache } = setup();
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  const input = screen.getByRole('textbox', { name: '快照名称' });
  expect(input).toHaveProperty('maxLength', 400);
  fireEvent.change(input, { target: { value: name } });
  fireEvent.click(screen.getByRole('button', { name: '保存快照名称' }));
  await screen.findByText('快照名称已保存。');
  const writes = fetcher.mock.calls.filter(
    ([, options]) => options.method === 'PATCH',
  );
  expect(writes).toHaveLength(1);
  expect(writes[0][0]).toBe(`/api/v1/snapshots/${snapshot.id}/`);
  expect(writes[0][1].body).toBe(JSON.stringify({ name }));
  expect(
    cache.getQueryData([
      'projects',
      'snapshot',
      snapshot.project_id,
      snapshot.id,
    ]),
  ).toEqual({ ...snapshot, name });
  for (const invalid of ['😀'.repeat(201), 'a'.repeat(201)]) {
    expect(() => parseSnapshot({ ...snapshot, name: invalid })).toThrow(
      '响应结构或资源归属无效',
    );
    expect(() =>
      renameSnapshot(snapshot, invalid, new AbortController().signal),
    ).toThrow('快照名称须为');
  }
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('保存取消在途旧详情和列表，迟到响应不会覆盖新名称或回填草稿', async () => {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const old = { ...snapshot, name: '原名称' };
  const page = { count: 1, next: null, previous: null, results: [old] };
  cache.setQueryData(
    ['projects', 'snapshot', snapshot.project_id, snapshot.id],
    old,
  );
  cache.setQueryData(['projects', 'snapshots', snapshot.project_id, 1], page);
  const releases: (() => void)[] = [],
    signals: AbortSignal[] = [];
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/')
      return new Response(JSON.stringify({ csrf_token: 'test-csrf' }));
    if (options.method === 'PATCH')
      return new Response(JSON.stringify({ ...old, name: '更新后名称' }));
    signals.push(options.signal as AbortSignal);
    return new Promise<Response>((resolve) =>
      releases.push(() =>
        resolve(
          new Response(
            JSON.stringify(path.includes('/snapshots/?') ? page : old),
          ),
        ),
      ),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  function ActiveQueries() {
    const detail = useQuery({
      queryKey: ['projects', 'snapshot', snapshot.project_id, snapshot.id],
      queryFn: ({ signal }) =>
        getSnapshot(snapshot.id, snapshot.project_id, signal),
    });
    const history = useQuery({
      queryKey: ['projects', 'snapshots', snapshot.project_id, 1],
      queryFn: ({ signal }) => listSnapshots(snapshot.project_id, 1, signal),
    });
    return (
      <>
        <SnapshotNameForm snapshot={detail.data ?? old} />
        <output aria-label="详情名称">{detail.data?.name}</output>
        <output aria-label="列表名称">{history.data?.results[0].name}</output>
      </>
    );
  }
  render(
    <QueryClientProvider client={cache}>
      <ActiveQueries />
    </QueryClientProvider>,
  );
  await waitFor(() => expect(releases).toHaveLength(2));
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  const input = screen.getByRole('textbox', { name: '快照名称' });
  fireEvent.change(input, { target: { value: '更新后名称' } });
  fireEvent.click(screen.getByRole('button', { name: '保存快照名称' }));
  await screen.findByText('快照名称已保存。');
  expect(signals.every((signal) => signal.aborted)).toBe(true);
  await act(async () => {
    releases.forEach((release) => release());
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  await waitFor(() => {
    expect(screen.getByLabelText('详情名称').textContent).toBe('更新后名称');
    expect(screen.getByLabelText('列表名称').textContent).toBe('更新后名称');
    expect(input).toHaveProperty('value', '更新后名称');
  });
  expect(
    fetcher.mock.calls.filter(([, options]) => options.method === 'PATCH'),
  ).toHaveLength(1);
});
