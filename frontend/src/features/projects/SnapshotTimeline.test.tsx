import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnapshotTimeline } from './SnapshotTimeline';

const project = '00000000-0000-0000-0000-000000000001';
const first = '00000000-0000-0000-0000-000000000002';
const second = '00000000-0000-0000-0000-000000000003';
const message =
  '当前项目只有一份快照，至少需要两份不同快照才能比较。请先导入第二份快照。';
function snapshot(id: string) {
  return {
    id,
    name: id === first ? '创建任务基线' : '',
    project_id: project,
    job_id: '00000000-0000-0000-0000-000000000004',
    created_at: '2026-10-01T00:00:00Z',
    source_extensions: ['.py'],
    summary: {
      entries: 9,
      accepted: 9,
      excluded: 0,
      skipped: 0,
      rejected: 0,
      declared_bytes: 22863,
      extracted_bytes: 22863,
      reasons: {},
    },
  };
}
function show(count: number) {
  const onSelect = vi.fn();
  const onCompare = vi.fn();
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const currentPage = new URL(path, 'http://local.test').searchParams.get(
        'page',
      );
      return new Response(
        JSON.stringify({
          count,
          next:
            count > 1 && currentPage === '1'
              ? `/api/v1/projects/${project}/snapshots/?page=2&page_size=20`
              : null,
          previous:
            currentPage === '2'
              ? `/api/v1/projects/${project}/snapshots/?page=1&page_size=20`
              : null,
          results: count
            ? [snapshot(currentPage === '2' ? second : first)]
            : [],
        }),
      );
    }),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SnapshotTimeline
        project={project}
        selected={first}
        onSelect={onSelect}
        onCompare={onCompare}
      />
    </QueryClientProvider>,
  );
  return { onSelect, onCompare };
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('只有一份快照时说明比较前置，保留已有快照和创建对比入口', async () => {
  const { onSelect, onCompare } = show(1);
  expect(await screen.findByText(message)).toBeTruthy();
  const item = screen.getByRole('button', { name: /导入快照 · 9 个文件/ });
  fireEvent.click(item);
  fireEvent.click(screen.getByRole('button', { name: '创建对比' }));
  expect(onSelect).toHaveBeenCalledWith(first);
  expect(onCompare).toHaveBeenCalledTimes(1);
});

test('项目有两份快照且每页仅一条时不会误报，分页和快照选择仍可用', async () => {
  const { onSelect } = show(2);
  await screen.findByRole('button', { name: /导入快照 · 9 个文件/ });
  expect(screen.queryByText(message)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '下一批记录' }));
  await screen.findByText('第 2 批');
  const item = await screen.findByRole('button', {
    name: /导入快照 · 9 个文件/,
  });
  fireEvent.click(item);
  expect(onSelect).toHaveBeenCalledWith(second);
  expect(screen.queryByText(message)).toBeNull();
});

test('没有快照时沿用空态，不显示只有一份快照的提示', async () => {
  show(0);
  expect(await screen.findByText('尚无导入快照。')).toBeTruthy();
  expect(screen.queryByText(message)).toBeNull();
  expect(screen.queryByRole('button', { name: /导入快照/ })).toBeNull();
});

test('时间线显示命名，旧空名显示时间回退，不显示内部快照编号', async () => {
  show(2);
  await screen.findByText('创建任务基线');
  expect(screen.queryByText(first.slice(0, 8))).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '下一批记录' }));
  await screen.findByText(/未命名快照 ·/);
  expect(screen.queryByText(second.slice(0, 8))).toBeNull();
});
