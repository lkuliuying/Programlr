import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type {
  Impact,
  Snapshot,
  SnapshotComparison,
} from '../../shared/api/generated/schema';
import { ComparisonWorkspace } from './ComparisonWorkspace';
import { ImpactResults } from './ImpactPanel';
import * as comparisonApi from './api/comparison-api';
import * as impactApi from './api/impact-api';
import * as projects from '../projects';
import { readSelection } from '../../app/workspace-location';

vi.mock('./api/comparison-api', async (original) => ({
  ...(await original()),
  listComparisons: vi.fn(),
  submitComparison: vi.fn(),
  getComparison: vi.fn(),
  listComparisonFiles: vi.fn(),
  getComparisonFile: vi.fn(),
}));
vi.mock('./api/impact-api', async (original) => ({
  ...(await original()),
  getComparisonImpact: vi.fn(),
}));
vi.mock('../jobs', () => ({
  queryJobs: vi
    .fn()
    .mockResolvedValue({ count: 0, next: null, previous: null, results: [] }),
}));
vi.mock('../projects', async (original) => ({
  ...(await original<typeof projects>()),
  listSnapshots: vi
    .fn()
    .mockResolvedValue({ count: 0, next: null, previous: null, results: [] }),
  listFiles: vi.fn().mockResolvedValue([]),
  getSnapshot: vi.fn(),
  SourceViewer: ({ snapshotId }: { snapshotId: string }) => (
    <p>只读源码 {snapshotId}</p>
  ),
}));
const id = (n: number) =>
  `00000000-0000-0000-0000-${String(n).padStart(12, '0')}`;
const time = '2026-10-01T00:00:00Z';
const input = {
  base_snapshot_id: id(2),
  target_snapshot_id: id(3),
  base_analysis_id: null,
  target_analysis_id: null,
};
const ref = {
  snapshot_id: id(2),
  file_path: 'models.py',
  start_line: 1,
  end_line: 2,
};
const comparison: SnapshotComparison = {
  id: id(4),
  project_id: id(1),
  job_id: id(5),
  ...input,
  comparison_version: 'snapshot-comparison/1.0.0',
  created_at: time,
  summary: { added: 0, deleted: 0, modified: 1, unchanged: 0 },
  comparability: 'files_only',
  comparison_notes: ['引用文件未变不等于讲解语义已验证。'],
  base_version: null,
  target_version: null,
  interfaces: [],
  relations: [],
  evidence: [
    {
      explanation_id: id(6),
      preview_id: id(7),
      analysis_id: id(8),
      endpoint_index: 0,
      references: [
        { source_ref: ref, target_ref: null, applicability: 'review' },
      ],
      warning: null,
    },
  ],
};
const file = {
  id: id(9),
  file_path: 'models.py',
  change_type: 'modified' as const,
  base_ref: ref,
  target_ref: { ...ref, snapshot_id: id(3) },
  base_sha256: 'a'.repeat(64),
  target_sha256: 'b'.repeat(64),
};
const emptyPage = { count: 0, next: null, previous: null, results: [] };
function unavailable(change: string | null = null) {
  return {
    comparison_id: comparison.id,
    change_id: change,
    include_candidates: false,
    base: {
      snapshot_id: id(2),
      analysis_id: null,
      available: false,
      reason: '未绑定分析，不能判断影响。',
      changed_files: [],
      impact: null,
    },
    target: {
      snapshot_id: id(3),
      analysis_id: null,
      available: false,
      reason: '未绑定分析，不能判断影响。',
      changed_files: [],
      impact: null,
    },
    limitations: ['两侧分别计算'],
  };
}
const props = () => ({
  projectId: id(1),
  snapshotId: id(3),
  comparisonId: null as string | null,
  changeId: null as string | null,
  candidates: false,
  onCandidates: vi.fn(),
  onComparison: vi.fn(),
  onChange: vi.fn(),
  onJob: vi.fn(),
  onSource: vi.fn(),
  onExplanation: vi.fn(),
});
function mount(element: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>{element}</QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(projects.getSnapshot).mockImplementation(
    async (snapshotId, projectId): Promise<Snapshot> => ({
      id: snapshotId,
      name: snapshotId === id(2) ? '基准教学快照' : '目标教学快照',
      project_id: projectId,
      job_id: id(5),
      created_at: time,
      source_extensions: ['.py'],
      source_manifest_names: [],
      preparation_status: 'pending',
      source_scan_id: null,
      scan_job_id: null,
      analysis_job_id: null,
      analysis_id: null,
      summary: {
        entries: 1,
        accepted: 1,
        excluded: 0,
        skipped: 0,
        rejected: 0,
        declared_bytes: 1,
        extracted_bytes: 1,
        reasons: {},
      },
    }),
  );
  vi.mocked(comparisonApi.listComparisons).mockResolvedValue(emptyPage);
  vi.mocked(comparisonApi.getComparison).mockResolvedValue(comparison);
  vi.mocked(comparisonApi.listComparisonFiles).mockResolvedValue({
    ...emptyPage,
    count: 1,
    results: [file],
  });
  vi.mocked(comparisonApi.getComparisonFile).mockResolvedValue({
    ...file,
    diff: '-old\n+new\n',
    base_ranges: [ref],
    target_ranges: [{ ...ref, snapshot_id: id(3) }],
  });
  vi.mocked(impactApi.getComparisonImpact).mockResolvedValue(unavailable());
});
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

test('明确两侧绑定，刷新后恢复同一输入和幂等键，不自动提交', async () => {
  const key = id(10),
    digest = Buffer.from(
      await webcrypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(JSON.stringify(input)),
      ),
    ).toString('hex');
  sessionStorage.setItem(
    `learning-lab.comparison-input.${id(1)}`,
    JSON.stringify(input),
  );
  sessionStorage.setItem(
    `learning-lab.operation.comparison.${id(1)}`,
    JSON.stringify({ key, digest }),
  );
  const callbacks = props();
  vi.mocked(comparisonApi.submitComparison).mockResolvedValue({
    id: id(5),
    kind: 'snapshot_comparison',
    status: 'queued',
    stage: 'queued',
    progress: null,
    snapshot_id: id(3),
    previous_job_id: null,
    parent_job_id: null,
    source_kind: '',
    result_deleted_at: null,
    result_deleted: false,
    result_url: null,
    error: null,
    created_at: time,
    updated_at: time,
  });
  mount(<ComparisonWorkspace {...callbacks} />);
  await screen.findByRole('button', { name: '恢复本次对比提交' });
  expect(comparisonApi.submitComparison).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '恢复本次对比提交' }));
  await waitFor(() => expect(callbacks.onJob).toHaveBeenCalledWith(id(5)));
  expect(comparisonApi.submitComparison).toHaveBeenCalledWith(
    id(1),
    input,
    key,
    expect.any(AbortSignal),
  );
  expect(
    sessionStorage.getItem(`learning-lab.comparison-input.${id(1)}`),
  ).toBeNull();
});

test('恢复输入损坏时保留未知操作，阻止新的提交', async () => {
  sessionStorage.setItem(`learning-lab.comparison-input.${id(1)}`, '{bad');
  mount(<ComparisonWorkspace {...props()} />);
  expect(await screen.findByText(/恢复输入损坏/)).toBeTruthy();
  expect(screen.getByRole('button', { name: '提交快照对比' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(comparisonApi.submitComparison).not.toHaveBeenCalled();
});

test('对比历史、双侧差异、旧引用和候选开关可以操作', async () => {
  const callbacks = {
    ...props(),
    comparisonId: comparison.id,
    changeId: file.id,
  };
  vi.mocked(impactApi.getComparisonImpact).mockResolvedValue(
    unavailable(file.id),
  );
  mount(<ComparisonWorkspace {...callbacks} />);
  expect((await screen.findByText(/^-old\s+\+new$/)).textContent).toBe(
    '-old\n+new\n',
  );
  expect(await screen.findByText(`只读源码 ${id(2)}`)).toBeTruthy();
  expect(screen.getByText(`只读源码 ${id(3)}`)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: '修改 · models.py' }));
  expect(screen.getByRole('table', { name: '文件变化' })).toBeTruthy();
  expect(callbacks.onChange).toHaveBeenCalledWith(file.id);
  fireEvent.click(screen.getByText(`讲解 ${id(6).slice(0, 8)}`));
  fireEvent.click(screen.getByRole('button', { name: '打开旧讲解' }));
  expect(callbacks.onExplanation).toHaveBeenCalledWith(
    comparison,
    id(6),
    id(8),
    0,
  );
  fireEvent.click(screen.getByRole('checkbox', { name: /包含未决候选/ }));
  expect(callbacks.onCandidates).toHaveBeenCalledWith(true);
});

test('对比与文件响应拒绝错误项目、引用快照和不成对分析', () => {
  expect(comparisonApi.parseComparison(comparison, id(4), id(1))).toEqual(
    comparison,
  );
  expect(() =>
    comparisonApi.parseComparison(
      { ...comparison, project_id: id(99) },
      id(4),
      id(1),
    ),
  ).toThrow();
  expect(() =>
    comparisonApi.parseComparisonInput({ ...input, base_analysis_id: id(8) }),
  ).toThrow();
  expect(() =>
    comparisonApi.parseComparisonFile(
      { ...file, base_ref: { ...ref, snapshot_id: id(3) } },
      comparison,
    ),
  ).toThrow();
  expect(() =>
    comparisonApi.parseComparisonFile(
      { ...file, change_type: 'unchanged' },
      comparison,
    ),
  ).toThrow();
  const selected = readSelection(
    `?project=${id(1)}&comparison=${id(4)}&change=${id(9)}&candidates=true`,
  );
  expect(selected.invalid).toBe(false);
  expect(selected.comparison).toBe(id(4));
  expect(selected.change).toBe(id(9));
  expect(selected.candidates).toBe(true);
  expect(readSelection(`?project=${id(1)}&change=${id(9)}`).invalid).toBe(true);
  expect(readSelection(`?project=${id(1)}&candidates=maybe`).invalid).toBe(
    true,
  );
});

function impact(): Impact {
  const node = {
    id: id(20),
    kind: 'endpoint' as const,
    name: 'GET /tasks/',
    source_ref: ref,
    evidence: [],
    endpoint: {
      index: 0,
      method: 'GET' as const,
      path: '/tasks/',
      path_kind: 'django_path' as const,
      action: 'get',
      is_candidate: false,
    },
    request: null,
  };
  return {
    analysis_id: id(8),
    snapshot_id: id(2),
    graph_version: 'analysis-graph/2.0.0',
    rule_version: 'python-drf/1.1.0',
    include_candidates: false,
    max_nodes: 200,
    max_edges: 400,
    starts: [node.id],
    nodes: [node],
    edges: [],
    relation_reviews: [],
    results: [
      {
        node,
        path_node_ids: [node.id],
        path_edge_ids: [],
        via_candidate: false,
      },
    ],
    visited_nodes: 1,
    visited_edges: 0,
    truncated: false,
    truncation_reasons: [],
    unmapped_files: ['unknown.py'],
    uncovered_files: ['unknown.py'],
    limitations: ['静态范围不代表运行轨迹'],
    diagnostics: [],
    diagnostics_url: `/api/v1/analyses/${id(8)}/diagnostics/`,
  };
}
test('影响依据联动源码，空结果和截断不能表示没有影响', async () => {
  const source = vi.fn(),
    data = impact();
  mount(<ImpactResults data={data} onSource={source} />);
  fireEvent.click(screen.getByText('GET /tasks/'));
  fireEvent.click(screen.getByRole('button', { name: 'models.py:1' }));
  expect(source).toHaveBeenCalledWith(ref, id(8));
  cleanup();
  mount(
    <ImpactResults
      data={{
        ...data,
        results: [],
        truncated: true,
        truncation_reasons: ['max_nodes'],
      }}
      onSource={source}
    />,
  );
  expect(screen.getByText(/不能说明没有影响/)).toBeTruthy();
  expect(screen.getByRole('alert').textContent).toContain('结果已截断');
});
test('影响路径必须来自对应图并保持候选状态，拒绝伪造路径和范围', () => {
  const data = impact();
  expect(impactApi.parseImpact(data, id(2), id(8), false)).toEqual(data);
  expect(() =>
    impactApi.parseImpact({ ...data, snapshot_id: id(3) }, id(2), id(8), false),
  ).toThrow();
  expect(() =>
    impactApi.parseImpact(
      { ...data, results: [{ ...data.results[0], path_edge_ids: [id(99)] }] },
      id(2),
      id(8),
      false,
    ),
  ).toThrow();
  expect(() =>
    impactApi.parseImpact(
      { ...data, results: [{ ...data.results[0], via_candidate: true }] },
      id(2),
      id(8),
      false,
    ),
  ).toThrow();
  expect(() =>
    impactApi.parseComparisonImpact(
      unavailable(id(99)),
      comparison,
      null,
      false,
    ),
  ).toThrow();
});
