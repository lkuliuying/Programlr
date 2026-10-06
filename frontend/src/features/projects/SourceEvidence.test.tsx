import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SourceEvidence } from './SourceEvidence';

const file = {
  id: '00000000-0000-0000-0000-000000000001',
  snapshot_id: '00000000-0000-0000-0000-000000000002',
  file_path: 'app/views.py',
  sha256: 'a'.repeat(64),
  size_bytes: 120,
  line_count: 20,
  encoding: 'utf-8',
};
const analysis = '00000000-0000-0000-0000-000000000003',
  scan = '00000000-0000-0000-0000-000000000004';
const reference = {
  snapshot_id: file.snapshot_id,
  file_path: file.file_path,
  start_line: 2,
  end_line: 5,
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('依据读取保持绑定分析、真实数量与数据分页，点击返回原始引用', async () => {
  const onSource = vi.fn();
  const fetcher = vi.fn(async (path: string) => {
    expect(path).toContain('analysis_id=' + analysis);
    expect(path).not.toContain('scan_id=');
    const page = new URL(path, 'http://local.test').searchParams.get('page');
    const base = `/api/v1/snapshots/${file.snapshot_id}/files/${file.id}/evidence/`;
    return new Response(
      JSON.stringify({
        count: 21,
        next:
          page === '1'
            ? base + '?page=2&page_size=20&analysis_id=' + analysis
            : null,
        previous:
          page === '2'
            ? base + '?page=1&page_size=20&analysis_id=' + analysis
            : null,
        results: [
          {
            id: 'a'.repeat(64),
            kind: 'interface',
            label: page === '1' ? '处理器依据' : '下一批依据',
            source_ref: reference,
          },
        ],
        snapshot_id: file.snapshot_id,
        file_id: file.id,
        analysis_id: analysis,
        scan_id: scan,
        scope: 'persisted_source_evidence',
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SourceEvidence
        file={file}
        analysisId={analysis}
        scanId={scan}
        onSource={onSource}
      />
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole('button', { name: /相关源码依据（21）/ }),
  );
  fireEvent.click(screen.getByRole('button', { name: /处理器依据/ }));
  expect(onSource).toHaveBeenCalledWith(reference);
  fireEvent.click(screen.getByRole('button', { name: '下一批记录' }));
  expect(await screen.findByText('下一批依据')).toBeTruthy();
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('无识别结果不请求，跨文件引用拒绝显示', async () => {
  const fetcher = vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'x',
              kind: 'knowledge',
              label: '错误归属',
              source_ref: { ...reference, file_path: 'else.py' },
            },
          ],
          snapshot_id: file.snapshot_id,
          file_id: file.id,
          analysis_id: null,
          scan_id: scan,
          scope: 'persisted_source_evidence',
        }),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <SourceEvidence file={file} onSource={vi.fn()} />
    </QueryClientProvider>,
  );
  fireEvent.click(screen.getByRole('button', { name: /相关源码依据/ }));
  expect(screen.getByText(/尚无可用识别结果/)).toBeTruthy();
  expect(fetcher).not.toHaveBeenCalled();
  view.rerender(
    <QueryClientProvider client={client}>
      <SourceEvidence file={file} scanId={scan} onSource={vi.fn()} />
    </QueryClientProvider>,
  );
  expect((await screen.findByRole('alert')).textContent).toContain(
    '资源归属无效',
  );
  expect(screen.queryByText('错误归属')).toBeNull();
});
