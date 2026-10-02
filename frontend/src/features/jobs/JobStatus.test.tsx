import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JobStatus } from './JobStatus';

const id = '00000000-0000-0000-0000-000000000001';
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function show() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <JobStatus
        id={id}
        snapshotId={null}
        onSelect={vi.fn()}
        onResult={vi.fn()}
      />
    </QueryClientProvider>,
  );
}
test('离开当前任务时取消尚未完成的读取', async () => {
  let signal: AbortSignal | null = null;
  vi.stubGlobal(
    'fetch',
    vi.fn((_path: string, options: RequestInit) => {
      signal = options.signal as AbortSignal;
      return new Promise(() => {});
    }),
  );
  const view = show();
  await waitFor(() => expect(signal).not.toBeNull());
  view.unmount();
  expect(signal!.aborted).toBe(true);
});
test('失败导入任务要求重新选择原 ZIP，展示错误追踪标识', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            id,
            kind: 'import',
            status: 'failed',
            stage: 'failed',
            created_at: '2026-09-29T00:00:00Z',
            updated_at: '2026-09-29T00:00:00Z',
            snapshot_id: null,
            previous_job_id: null,
            progress: null,
            result_url: null,
            error: {
              code: 'IMPORT_FAILED',
              message: '导入未完成',
              request_id: 'synthetic-trace',
              details: {},
            },
          }),
        ),
    ),
  );
  show();
  expect(await screen.findByLabelText('重新选择原 ZIP')).toBeTruthy();
  expect(screen.getByRole('alert').textContent).toContain('synthetic-trace');
  expect(screen.getByRole('button', { name: '创建重试任务' })).toBeTruthy();
});
