import { afterEach, expect, test, vi } from 'vitest';
import { resolveJobResult } from './job-result-location';
import type { Job } from '../shared/api/generated/schema';
import { readSelection, resolveWorkspaceSection } from './workspace-location';
const id = '00000000-0000-0000-0000-000000000001';
const snapshotId = '00000000-0000-0000-0000-000000000002';
const projectId = '00000000-0000-0000-0000-000000000003';
const time = '2026-10-03T00:00:00Z';
const job: Job = {
  id,
  kind: 'import',
  status: 'succeeded',
  snapshot_id: snapshotId,
  result_url: `/api/v1/snapshots/${snapshotId}/`,
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
const snapshot = {
  id: snapshotId,
  project_id: projectId,
  name: '',
  job_id: id,
  created_at: time,
  source_extensions: ['.py'],
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
afterEach(() => vi.unstubAllGlobals());
test('通知结果先读取归属，进入原项目，而不采用当前工作区项目', async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify(snapshot)));
  vi.stubGlobal('fetch', fetcher);
  expect(await resolveJobResult(job, new AbortController().signal)).toEqual({
    project: projectId,
    snapshot: snapshotId,
    section: 'workbench',
  });
  expect(fetcher).toHaveBeenCalledOnce();
});
test.each([
  { ...snapshot, job_id: projectId },
  { ...snapshot, id: projectId },
])('拒绝其他任务或错误资源结果', async (value) => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(value))),
  );
  await expect(
    resolveJobResult(job, new AbortController().signal),
  ).rejects.toThrow('归属');
});
test('独立course旧链接无接口前置，curriculum/goal仍保留原归属约束', () => {
  const course = readSelection(`?course=${id}`);
  expect(course.invalid).toBe(false);
  expect(course.course).toBe(id);
  expect(resolveWorkspaceSection(course)).toBe('learning');
  expect(readSelection(`?course=${id}&course=${id}`).invalid).toBe(true);
  expect(readSelection(`?curriculum=${id}`).invalid).toBe(true);
});
