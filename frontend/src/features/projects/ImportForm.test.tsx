import { webcrypto } from 'node:crypto';
import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ImportForm } from './ProjectNavigator';
import { importArchive } from './api/projects-api';
import { MAX_ARCHIVE_BYTES } from './archive-validation';

const project = '00000000-0000-0000-0000-000000000001';
const job = {
  id: '00000000-0000-0000-0000-000000000002',
  kind: 'import',
  status: 'queued',
  stage: 'queued',
  snapshot_id: null,
  previous_job_id: null,
  progress: null,
  error: null,
  result_url: null,
  created_at: '2026-10-02T00:00:00Z',
  updated_at: '2026-10-02T00:00:00Z',
};
const response = (data: unknown) => new Response(JSON.stringify(data));
function archive(name = 'example.zip', size = 5) {
  const file = new File([new Uint8Array(size)], name);
  Object.defineProperty(file, 'arrayBuffer', {
    value: async () => new Uint8Array(size).buffer,
  });
  return file;
}
function setup() {
  vi.stubGlobal('crypto', webcrypto);
  const cache = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  const onJob = vi.fn();
  render(
    <QueryClientProvider client={cache}>
      <ImportForm projectId={project} onJob={onJob} />
    </QueryClientProvider>,
  );
  const input = screen.getByLabelText('导入源码 ZIP');
  const choose = (file: File) =>
    fireEvent.change(input, { target: { files: [file] } });
  return { input, choose, onJob };
}
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

test.each([
  ['example.txt', 5, 'ZIP 格式'],
  ['empty.zip', 0, '文件是空的'],
  ['large.zip', MAX_ARCHIVE_BYTES + 1, '超过 20 MiB'],
])(
  '选择无效文件 %s 立即说明原因，阻止提交且不创建恢复记录',
  (name, size, message) => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    const { input, choose } = setup();
    expect(screen.getByRole('button', { name: '导入为新快照' })).toHaveProperty(
      'disabled',
      true,
    );
    choose(archive(name, size));
    expect(screen.getByRole('alert').textContent).toContain(message);
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toContain(
      screen.getByRole('alert').id,
    );
    fireEvent.submit(input.closest('form')!);
    expect(fetcher).not.toHaveBeenCalled();
    expect(sessionStorage.length).toBe(0);
  },
);

test('换成有效文件后移除旧校验，文件大小可读，移除后焦点回到文件控件', () => {
  const { input, choose } = setup();
  choose(archive('wrong.txt'));
  choose(archive('教学示例.ZIP', 2048));
  expect(screen.queryByRole('alert')).toBeNull();
  expect(screen.getByRole('status').textContent).toContain('教学示例.ZIP');
  expect(screen.getByRole('status').textContent).toContain('2,048 字节');
  expect(screen.getByRole('button', { name: '导入为新快照' })).toHaveProperty(
    'disabled',
    false,
  );
  fireEvent.click(screen.getByRole('button', { name: '移除文件' }));
  expect(screen.queryByRole('status')).toBeNull();
  expect(document.activeElement).toBe(input);
  expect(input).toHaveProperty('value', '');
  expect(screen.getByRole('button', { name: '导入为新快照' })).toHaveProperty(
    'disabled',
    true,
  );
});

test('API 边界接受恰好 20 MiB，拒绝多一字节且拒绝时不发 CSRF 或上传请求', async () => {
  const fetcher = vi.fn(async (path: string) =>
    response(path === '/api/v1/csrf/' ? { csrf_token: 'test-csrf' } : job),
  );
  vi.stubGlobal('fetch', fetcher);
  const signal = new AbortController().signal;
  await expect(
    importArchive(
      project,
      archive('boundary.ZIP', MAX_ARCHIVE_BYTES),
      'test-key',
      signal,
    ),
  ).resolves.toEqual(job);
  expect(fetcher).toHaveBeenCalledTimes(2);
  fetcher.mockClear();
  expect(() =>
    importArchive(
      project,
      archive('too-large.zip', MAX_ARCHIVE_BYTES + 1),
      'test-key',
      signal,
    ),
  ).toThrow('超过 20 MiB');
  expect(fetcher).not.toHaveBeenCalled();
});

test('连续提交只上传一次，成功后进入任务且清除恢复标识', async () => {
  const fetcher = vi.fn(async (path: string) =>
    response(path === '/api/v1/csrf/' ? { csrf_token: 'test-csrf' } : job),
  );
  vi.stubGlobal('fetch', fetcher);
  const { input, choose, onJob } = setup();
  choose(archive());
  fireEvent.submit(input.closest('form')!);
  fireEvent.submit(input.closest('form')!);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith(job.id));
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(sessionStorage.length).toBe(0);
});

test('未知提交不自动重试，移除文件不删除恢复标识，相同文件恢复复用原操作键', async () => {
  const keys: string[] = [];
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (path === '/api/v1/csrf/') return response({ csrf_token: 'test-csrf' });
    keys.push((options.headers as Record<string, string>)['Idempotency-Key']!);
    if (keys.length === 1) throw new TypeError('网络暂不可用');
    return response(job);
  });
  vi.stubGlobal('fetch', fetcher);
  const { input, choose, onJob } = setup();
  choose(archive());
  fireEvent.submit(input.closest('form')!);
  await screen.findByText(/连接未完成/);
  expect(keys).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: '移除文件' }));
  expect(sessionStorage.length).toBe(1);
  choose(archive());
  expect(
    screen.getByRole('button', { name: '恢复原 ZIP 导入' }),
  ).toHaveProperty('disabled', false);
  fireEvent.submit(input.closest('form')!);
  await waitFor(() => expect(onJob).toHaveBeenCalledWith(job.id));
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  expect(sessionStorage.length).toBe(0);
});
