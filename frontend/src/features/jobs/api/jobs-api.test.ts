import { expect, test } from 'vitest';
import { parseJob, parsePage } from './jobs-api';

const job = {
  id: 'job-test',
  kind: 'system_check',
  status: 'queued',
  stage: 'queued',
  created_at: '2026-09-29T00:00:00Z',
  updated_at: '2026-09-29T00:00:00Z',
  snapshot_id: null,
  previous_job_id: null,
  progress: null,
  result_url: null,
  error: null,
};

test('任务历史接受原任务关联，拒绝畸形或自引用标识', () => {
  const previous = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const retry = { ...job, previous_job_id: previous };
  expect(
    parsePage({ count: 2, next: null, previous: null, results: [job, retry] })
      .results[1].previous_job_id,
  ).toBe(previous);
  for (const invalid of [
    undefined,
    '',
    42,
    {},
    'invalid',
    'https://invalid.example/',
  ])
    expect(() => parseJob({ ...job, previous_job_id: invalid })).toThrow();
  expect(() => parseJob({ ...retry, id: previous })).toThrow();
});
test('拒绝未知任务状态、非同源结果和缺失字段', () => {
  expect(parseJob(job).status).toBe('queued');
  for (const invalid of [
    null,
    {},
    { ...job, status: 'unknown' },
    { ...job, status: ['queued'] },
    { ...job, result_url: 'https://invalid.example/' },
    { ...job, error: {} },
  ])
    expect(() => parseJob(invalid)).toThrow();
});

test('删除后历史导入、分析和实验只读取摘要，不要求已清理结果链接', () => {
  const snapshot = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  for (const kind of [
    'import',
    'analysis',
    'explanation',
    'source_scan',
    'snapshot_comparison',
    'lab',
  ]) {
    const removed = {
      ...job,
      kind,
      status: 'succeeded',
      snapshot_id: kind === 'lab' ? null : snapshot,
      result_deleted: true,
      result_deleted_at: '2026-10-03T00:00:00Z',
    };
    expect(parseJob(removed).result_deleted).toBe(true);
    expect(() =>
      parseJob({ ...removed, result_url: `/api/v1/analyses/${snapshot}/` }),
    ).toThrow();
  }
});
test('验证空列表和分页边界', () => {
  expect(
    parsePage({ count: 0, next: null, previous: null, results: [] }).results,
  ).toEqual([]);
  expect(() =>
    parsePage({
      count: 1,
      next: '//invalid.example',
      previous: null,
      results: [job],
    }),
  ).toThrow();
  expect(() =>
    parsePage({ count: -1, next: null, previous: null, results: [] }),
  ).toThrow();
});

test('导入记录与快照绑定，不能混用基础检查结果', () => {
  const snapshot = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const imported = {
    ...job,
    kind: 'import',
    status: 'succeeded',
    snapshot_id: snapshot,
    result_url: `/api/v1/snapshots/${snapshot}/`,
  };
  expect(parseJob(imported).snapshot_id).toBe(snapshot);
  expect(parseJob({ ...job, kind: 'import' }).status).toBe('queued');
  for (const invalid of [
    { ...imported, snapshot_id: null },
    { ...imported, snapshot_id: 'different' },
    { ...imported, status: 'failed' },
    { ...imported, result_url: `/api/v1/system-checks/${snapshot}/` },
  ])
    expect(() => parseJob(invalid)).toThrow();
});

test('分析记录始终绑定快照且只接受分析结果地址', () => {
  const snapshot = '9d8df4d4-d2c7-4c58-886d-8f0084f29652';
  const queued = { ...job, kind: 'analysis', snapshot_id: snapshot };
  const completed = {
    ...queued,
    status: 'succeeded',
    result_url: `/api/v1/analyses/${snapshot}/`,
  };
  expect(parseJob(queued).snapshot_id).toBe(snapshot);
  expect(parseJob(completed).status).toBe('succeeded');
  for (const invalid of [
    { ...queued, snapshot_id: null },
    { ...completed, result_url: null },
    { ...completed, result_url: `/api/v1/system-checks/${snapshot}/` },
    { ...completed, status: 'failed' },
  ])
    expect(() => parseJob(invalid)).toThrow();
});
