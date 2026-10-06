import { afterEach, expect, test, vi } from 'vitest';
import { resolveJobResult } from './job-result-location';
import type {
  Job,
  Snapshot,
  Analysis,
  SnapshotComparison,
} from '../shared/api/generated/schema';

const id = (number: number) =>
  `00000000-0000-0000-0000-${String(number).padStart(12, '0')}`;
const time = '2026-10-03T00:00:00Z';
const snapshot: Snapshot = {
  id: id(2),
  project_id: id(3),
  name: '合成结果归属快照',
  job_id: id(9),
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
};
const analysis: Analysis = {
  id: id(4),
  snapshot_id: snapshot.id,
  job_id: id(1),
  root_urlconf: 'config.urls',
  source_scan_id: null,
  rule_version: 'synthetic/1',
  created_at: time,
  frontend: null,
  coverage: {
    python_files: 1,
    parsed_files: 1,
    syntax_failed_files: 0,
    skipped_files: 0,
    endpoint_count: 2,
    diagnostic_count: 0,
    complete: true,
    limitations: [],
  },
};
const comparison: SnapshotComparison = {
  id: id(5),
  project_id: snapshot.project_id,
  job_id: id(1),
  base_snapshot_id: snapshot.id,
  target_snapshot_id: id(6),
  base_analysis_id: null,
  target_analysis_id: null,
  comparison_version: 'snapshot-comparison/1.0.0',
  created_at: time,
  summary: { added: 1, deleted: 0, modified: 0, unchanged: 0 },
  comparability: 'files_only',
  comparison_notes: [],
  base_version: null,
  target_version: null,
  interfaces: [],
  relations: [],
  evidence: [],
};
function job(
  kind: string,
  path: string,
  snapshotId: string | null = null,
): Job {
  return {
    id: id(1),
    kind,
    status: 'succeeded',
    result_url: path,
    snapshot_id: snapshotId,
    previous_job_id: null,
    parent_job_id: null,
    source_kind: '',
    result_deleted_at: null,
    result_deleted: false,
    stage: 'completed',
    progress: null,
    error: null,
    created_at: time,
    updated_at: time,
  };
}
function responses(result: unknown) {
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    expect(options.method).toBeUndefined();
    expect(path.startsWith('/api/v1/')).toBe(true);
    const value =
      path === `/api/v1/snapshots/${snapshot.id}/`
        ? snapshot
        : path === `/api/v1/analyses/${analysis.id}/`
          ? analysis
          : result;
    return new Response(JSON.stringify(value));
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
afterEach(() => vi.unstubAllGlobals());

test('系统检查结果读取并核验任务与URL归属，只有GET', async () => {
  const path = `/api/v1/system-checks/${id(8)}/`;
  const fetcher = responses({
    id: id(8),
    job_id: id(1),
    check_version: '1',
    database: 'passed',
    queue: 'passed',
    worker: 'passed',
    completed_at: time,
  });
  expect(
    await resolveJobResult(
      job('system_check', path),
      new AbortController().signal,
    ),
  ).toEqual({ check: path });
  expect(fetcher).toHaveBeenCalledExactlyOnceWith(
    path,
    expect.objectContaining({ credentials: 'same-origin' }),
  );
});

test.each([
  { id: id(8), job_id: id(9) },
  { id: id(9), job_id: id(1) },
])('系统检查拒绝其他任务或错误结果ID', async (foreign) => {
  responses({
    ...foreign,
    check_version: '1',
    database: 'passed',
    queue: 'passed',
    worker: 'passed',
    completed_at: time,
  });
  await expect(
    resolveJobResult(
      job('system_check', `/api/v1/system-checks/${id(8)}/`),
      new AbortController().signal,
    ),
  ).rejects.toThrow('归属');
});

test('分析结果从其快照读取项目归属，返回明确API入口', async () => {
  responses(analysis);
  expect(
    await resolveJobResult(
      job('analysis', `/api/v1/analyses/${analysis.id}/`, snapshot.id),
      new AbortController().signal,
    ),
  ).toEqual({
    project: snapshot.project_id,
    snapshot: snapshot.id,
    analysis: analysis.id,
    section: 'api',
  });
});

test('分析结果属于其他任务时拒绝导航', async () => {
  const fetcher = vi.fn(
    async (path: string) =>
      new Response(
        JSON.stringify(
          path.startsWith('/api/v1/snapshots/')
            ? snapshot
            : { ...analysis, job_id: id(10) },
        ),
      ),
  );
  vi.stubGlobal('fetch', fetcher);
  await expect(
    resolveJobResult(
      job('analysis', `/api/v1/analyses/${analysis.id}/`, snapshot.id),
      new AbortController().signal,
    ),
  ).rejects.toThrow('归属');
});

test('快照比较恢复基线快照与比较ID，无分析的文件比较保留null', async () => {
  responses(comparison);
  expect(
    await resolveJobResult(
      job(
        'snapshot_comparison',
        `/api/v1/snapshot-comparisons/${comparison.id}/`,
        comparison.target_snapshot_id,
      ),
      new AbortController().signal,
    ),
  ).toEqual({
    project: comparison.project_id,
    snapshot: comparison.base_snapshot_id,
    analysis: null,
    comparison: comparison.id,
    section: 'comparison',
  });
});

test.each([
  { ...comparison, job_id: id(10) },
  { ...comparison, target_snapshot_id: id(10) },
])('快照比较拒绝其他任务或目标快照', async (foreign) => {
  responses(foreign);
  await expect(
    resolveJobResult(
      job(
        'snapshot_comparison',
        `/api/v1/snapshot-comparisons/${comparison.id}/`,
        comparison.target_snapshot_id,
      ),
      new AbortController().signal,
    ),
  ).rejects.toThrow('归属');
});

test('未成功任务不读取结果资源，也不会外发或创建记录', async () => {
  const fetcher = responses({});
  await expect(
    resolveJobResult(
      {
        ...job('analysis', `/api/v1/analyses/${analysis.id}/`, snapshot.id),
        status: 'running',
        result_url: null,
      },
      new AbortController().signal,
    ),
  ).rejects.toThrow('归属');
  expect(fetcher).not.toHaveBeenCalled();
});
