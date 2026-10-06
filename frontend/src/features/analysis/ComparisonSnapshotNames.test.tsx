import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ComparisonWorkspace } from './ComparisonWorkspace';
import * as comparisonApi from './api/comparison-api';
import type { SnapshotComparison } from '../../shared/api/generated/schema';

vi.mock('./api/comparison-api', async (original) => ({
  ...(await original()),
  listComparisons: vi
    .fn()
    .mockResolvedValue({ count: 0, next: null, previous: null, results: [] }),
  getComparison: vi.fn(),
  getComparisonFile: vi.fn(),
  listComparisonFiles: vi.fn(),
}));
vi.mock('./ImpactPanel', () => ({ ComparisonImpactPanel: () => null }));
vi.mock('../jobs', () => ({
  queryJobs: vi
    .fn()
    .mockResolvedValue({ count: 0, next: null, previous: null, results: [] }),
}));
const id = (n: number) =>
  `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
const project = id(1),
  first = id(2),
  selected = id(3);
function snapshot(n: number) {
  return {
    id: id(n),
    project_id: project,
    job_id: id(4),
    name: n === 2 ? '初始基线' : '增加请求校验',
    created_at: '2026-10-01T00:00:00Z',
    source_extensions: ['.py'],
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
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

test('对比两侧源码从各自服务端快照名称读取，旧空名称用日期回退且不露短UUID', async () => {
  const comparison: SnapshotComparison = {
    id: id(10),
    project_id: project,
    job_id: id(11),
    base_snapshot_id: first,
    target_snapshot_id: selected,
    base_analysis_id: null,
    target_analysis_id: null,
    comparison_version: 'snapshot-comparison/1.0.0',
    created_at: '2026-10-01T00:00:00Z',
    summary: { added: 0, deleted: 0, modified: 1, unchanged: 0 },
    comparability: 'files_only',
    comparison_notes: [],
    base_version: null,
    target_version: null,
    interfaces: [],
    relations: [],
    evidence: [],
  };
  const name = '对比基准请求校验快照'.repeat(14);
  const sources = [first, selected].map((snapshotId, index) => ({
    id: id(20 + index),
    snapshot_id: snapshotId,
    file_path: 'views.py',
    sha256: (index === 0 ? 'a' : 'b').repeat(64),
    size_bytes: 1,
    line_count: 1,
    encoding: 'utf-8',
  }));
  const reference = (snapshotId: string) => ({
    snapshot_id: snapshotId,
    file_path: 'views.py',
    start_line: 1,
    end_line: 1,
  });
  const file = {
    id: id(12),
    file_path: 'views.py',
    change_type: 'modified' as const,
    base_ref: reference(first),
    target_ref: reference(selected),
    base_sha256: 'a'.repeat(64),
    target_sha256: 'b'.repeat(64),
  };
  vi.mocked(comparisonApi.getComparison).mockResolvedValue(comparison);
  vi.mocked(comparisonApi.listComparisonFiles).mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [file],
  });
  vi.mocked(comparisonApi.getComparisonFile).mockResolvedValue({
    ...file,
    diff: '',
    base_ranges: [],
    target_ranges: [],
  });
  const fetcher = vi.fn(async (path: string) => {
    const source = sources.find((item) => path.includes(item.snapshot_id));
    if (path.includes('/content/'))
      return new Response(
        JSON.stringify({
          ...source,
          start_line: 1,
          end_line: 1,
          content:
            source?.snapshot_id === first ? '基准源码内容\n' : '目标源码内容\n',
        }),
      );
    if (path.includes('/files/?'))
      return new Response(
        JSON.stringify({
          count: 1,
          next: null,
          previous: null,
          results: [source],
        }),
      );
    if (path === `/api/v1/snapshots/${first}/`)
      return new Response(JSON.stringify({ ...snapshot(2), name }));
    if (path === `/api/v1/snapshots/${selected}/`)
      return new Response(JSON.stringify({ ...snapshot(3), name: '' }));
    return new Response(
      JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={cache}>
      <ComparisonWorkspace
        projectId={project}
        snapshotId={selected}
        comparisonId={comparison.id}
        changeId={file.id}
        candidates={false}
        onCandidates={vi.fn()}
        onComparison={vi.fn()}
        onChange={vi.fn()}
        onJob={vi.fn()}
        onSource={vi.fn()}
        onExplanation={vi.fn()}
      />
    </QueryClientProvider>,
  );
  await screen.findByText('基准源码内容');
  await screen.findByText('目标源码内容');
  const panels = screen.getAllByRole('region', { name: '只读源码' });
  expect(within(panels[0]).getByText(`快照 ${name} · 只读`)).toBeTruthy();
  expect(
    within(panels[1]).getByText(/快照 未命名快照 · .* · 只读/),
  ).toBeTruthy();
  for (const panel of panels)
    expect(panel.querySelector('.source-meta')?.textContent).not.toContain(
      first.slice(0, 8),
    );
  expect(
    cache.getQueryData(['projects', 'snapshot', project, first]),
  ).toMatchObject({ id: first, name });
  expect(
    cache.getQueryData(['projects', 'snapshot', project, selected]),
  ).toMatchObject({ id: selected, name: '' });
});

test('对比选择使用名称，跨页所选快照通过归属校验的详情恢复名称', async () => {
  const fetcher = vi.fn(async (path: string) => {
    if (path === `/api/v1/snapshots/${selected}/`)
      return new Response(JSON.stringify(snapshot(3)));
    const page = new URL(path, 'http://local.test').searchParams.get('page');
    return new Response(
      JSON.stringify({
        count: 2,
        next:
          page === '1'
            ? `/api/v1/projects/${project}/snapshots/?page=2&page_size=20`
            : null,
        previous:
          page === '2'
            ? `/api/v1/projects/${project}/snapshots/?page=1&page_size=20`
            : null,
        results: [snapshot(page === '2' ? 3 : 2)],
      }),
    );
  });
  vi.stubGlobal('fetch', fetcher);
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={cache}>
      <ComparisonWorkspace
        projectId={project}
        snapshotId={selected}
        comparisonId={null}
        changeId={null}
        candidates={false}
        onCandidates={vi.fn()}
        onComparison={vi.fn()}
        onChange={vi.fn()}
        onJob={vi.fn()}
        onSource={vi.fn()}
        onExplanation={vi.fn()}
      />
    </QueryClientProvider>,
  );
  const target = within(screen.getByRole('group', { name: '目标快照与分析' }));
  await target.findByRole('option', { name: '增加请求校验' });
  expect(target.getByRole('combobox', { name: '目标快照' })).toHaveProperty(
    'value',
    selected,
  );
  expect(screen.queryByText(`已选 ${selected}`)).toBeNull();
  expect(screen.queryByText(first.slice(0, 8))).toBeNull();
  const snapshotPager = within(
    target.getAllByRole('navigation', { name: '记录分页' })[0],
  );
  fireEvent.click(snapshotPager.getByRole('button', { name: '下一批记录' }));
  await target.findByText('第 2 批');
  expect(target.getByRole('option', { name: '增加请求校验' })).toHaveProperty(
    'value',
    selected,
  );
  expect(
    fetcher.mock.calls.filter(
      ([path]) => path === `/api/v1/snapshots/${selected}/`,
    ),
  ).toHaveLength(1);
});
