import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SourceViewer } from './SourceViewer';
import { parseFile } from './api/projects-api';
import type { SourceRef } from '../../shared/api/generated/schema';

const snapshot = '00000000-0000-0000-0000-000000000001';
const file = {
  id: '00000000-0000-0000-0000-000000000002',
  snapshot_id: snapshot,
  file_path: 'entry.ts',
  sha256: 'a'.repeat(64),
  line_count: 300,
  size_bytes: 600,
  encoding: 'utf-8',
};
const reference = {
  snapshot_id: snapshot,
  file_path: 'entry.ts',
  start_line: 1,
  end_line: 300,
};
function show(ref: SourceRef, snapshotName?: string) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SourceViewer
        files={[file]}
        snapshotId={snapshot}
        snapshotName={snapshotName}
        reference={ref}
      />
    </QueryClientProvider>,
  );
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('越界、缺失文件和跨快照来源不读取任何源码', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  for (const bad of [
    { ...reference, end_line: 301 },
    { ...reference, file_path: 'missing.ts' },
    { ...reference, snapshot_id: file.id },
  ]) {
    const view = show(bad, '相同显示名称不能替代 UUID 归属');
    expect(screen.getByRole('alert').textContent).toContain('引用失效');
    view.unmount();
  }
  expect(fetcher).not.toHaveBeenCalled();
  expect(() =>
    parseFile({ ...file, snapshot_id: file.id }, snapshot),
  ).toThrow();
});
test('长引用按 200 行读取，下一段不混入前段内容', async () => {
  const paths: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      paths.push(path);
      const params = new URL(path, 'http://local.test').searchParams;
      const start = Number(params.get('start_line')),
        end = Number(params.get('end_line'));
      return new Response(
        JSON.stringify({
          ...file,
          start_line: start,
          end_line: end,
          content:
            Array.from(
              { length: end - start + 1 },
              (_, index) => `第 ${start + index} 行`,
            ).join('\n') + '\n',
        }),
      );
    }),
  );
  show(reference);
  await screen.findByText('第 1 行');
  fireEvent.click(screen.getByRole('button', { name: '下一段' }));
  await screen.findByText('第 201 行');
  expect(screen.queryByText('第 1 行')).toBeNull();
  expect(paths.map((path) => path.split('?')[1])).toEqual([
    'start_line=1&end_line=200',
    'start_line=201&end_line=300',
  ]);
});
test('源码响应摘要或文件身份不符时明确失败', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            ...file,
            sha256: 'b'.repeat(64),
            start_line: 1,
            end_line: 1,
            content: '错误内容\n',
          }),
        ),
    ),
  );
  show({ ...reference, end_line: 1 }, '名称正确但摘要错误');
  expect((await screen.findByRole('alert')).textContent).toContain(
    '资源归属无效',
  );
  expect(screen.queryByText('错误内容')).toBeNull();
});

test('源码元数据完整显示长名称作为文本，省略或空名兼容未命名状态且不展示短编号', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            ...file,
            start_line: 1,
            end_line: 1,
            content: 'const task = 1;\n',
          }),
        ),
    ),
  );
  const longName =
    '创建任务请求校验基线'.repeat(14) + '<img src=x onerror=alert(1)>';
  for (const name of [undefined, '', longName]) {
    const view = show({ ...reference, end_line: 1 }, name);
    expect((await screen.findByLabelText('entry.ts 源码行')).textContent).toBe(
      'const task = 1;',
    );
    const metadata = view.container.querySelector('.source-meta small');
    expect(metadata?.textContent).toBe(`快照 ${name || '未命名快照'} · 只读`);
    expect(metadata?.getAttribute('title')).toBe(name || '未命名快照');
    expect(metadata?.textContent).not.toContain(snapshot.slice(0, 8));
    expect(view.container.querySelector('img')).toBeNull();
    view.unmount();
  }
});
