import {
  ApiError,
  isRecord,
  requestJson,
  submitJson,
  submitBody,
} from '../../../shared/api/client';
import type {
  Job,
  JobPage,
  SystemCheck,
} from '../../../shared/api/generated/schema';
import { page as decodePage } from '../../../shared/api/validation';

export function parseJob(value: unknown): Job {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    typeof value.kind !== 'string' ||
    ![
      'system_check',
      'import',
      'analysis',
      'explanation',
      'lab',
      'snapshot_comparison',
    ].includes(value.kind) ||
    typeof value.status !== 'string' ||
    !['queued', 'running', 'succeeded', 'failed'].includes(value.status) ||
    typeof value.stage !== 'string' ||
    typeof value.created_at !== 'string' ||
    typeof value.updated_at !== 'string' ||
    (value.snapshot_id !== null &&
      (!['import', 'analysis', 'explanation', 'snapshot_comparison'].includes(
        String(value.kind),
      ) ||
        typeof value.snapshot_id !== 'string')) ||
    (value.previous_job_id !== null &&
      (typeof value.previous_job_id !== 'string' ||
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(
          value.previous_job_id,
        ) ||
        value.previous_job_id === value.id)) ||
    value.progress !== null ||
    (value.result_url !== null &&
      (typeof value.result_url !== 'string' ||
        !(
          value.kind === 'import'
            ? /^\/api\/v1\/snapshots\/[0-9a-f-]+\/$/
            : value.kind === 'analysis'
              ? /^\/api\/v1\/analyses\/[0-9a-f-]+\/$/
              : value.kind === 'explanation'
                ? /^\/api\/v1\/explanations\/[0-9a-f-]+\/$/
                : value.kind === 'snapshot_comparison'
                  ? /^\/api\/v1\/snapshot-comparisons\/[0-9a-f-]+\/$/
                  : value.kind === 'lab'
                    ? /^\/api\/v1\/(?:lab-runs|system-lab-runs)\/[0-9a-f-]+\/$/
                    : /^\/api\/v1\/system-checks\/[0-9a-f-]+\/$/
        ).test(value.result_url))) ||
    (value.error !== null &&
      (!isRecord(value.error) ||
        typeof value.error.code !== 'string' ||
        typeof value.error.message !== 'string' ||
        typeof value.error.request_id !== 'string' ||
        !isRecord(value.error.details)))
  ) {
    throw new ApiError('任务响应格式无效。', 0);
  }
  if (
    value.kind === 'import' &&
    (value.status === 'succeeded'
      ? typeof value.snapshot_id !== 'string' ||
        value.result_url !== `/api/v1/snapshots/${value.snapshot_id}/`
      : value.snapshot_id !== null || value.result_url !== null)
  ) {
    throw new ApiError('导入任务的快照归属无效。', 0);
  }
  if (
    ['analysis', 'explanation', 'snapshot_comparison'].includes(
      String(value.kind),
    ) &&
    (typeof value.snapshot_id !== 'string' ||
      !/^[0-9a-f-]{36}$/.test(value.snapshot_id) ||
      (value.status === 'succeeded'
        ? value.result_url === null
        : value.result_url !== null))
  ) {
    throw new ApiError('分析任务的快照或结果归属无效。', 0);
  }
  if (
    value.kind === 'lab' &&
    (value.snapshot_id !== null ||
      (value.status === 'succeeded'
        ? value.result_url === null
        : value.result_url !== null))
  )
    throw new ApiError('实验任务的来源或结果无效。', 0);
  // 运行时逐字段校验后才收窄为生成类型，禁止把未校验 JSON 直接当作 DTO。
  return value as Job;
}

export function parsePage(value: unknown): JobPage {
  if (
    !isRecord(value) ||
    !Number.isInteger(value.count) ||
    Number(value.count) < 0 ||
    !Array.isArray(value.results) ||
    ![value.next, value.previous].every(
      (link) =>
        link === null ||
        (typeof link === 'string' &&
          /^\/api\/v1\/jobs\/\?page=\d+&page_size=\d+$/.test(link)),
    )
  )
    throw new ApiError('任务列表格式无效。', 0);
  const results = value.results.map(parseJob);
  return {
    count: Number(value.count),
    next: typeof value.next === 'string' ? value.next : null,
    previous: typeof value.previous === 'string' ? value.previous : null,
    results,
  };
}

export const listJobs = (page: number, signal: AbortSignal) =>
  requestJson(`/api/v1/jobs/?page=${page}&page_size=20`, parsePage, { signal });
export const submitCheck = (key: string) =>
  submitJson('/api/v1/system-checks/', key, parseJob);
export const getJob = (id: string, signal: AbortSignal) =>
  requestJson(
    `/api/v1/jobs/${id}/`,
    (value) => {
      const job = parseJob(value);
      if (job.id !== id) throw new ApiError('任务归属无效。', 0);
      return job;
    },
    { signal },
  );
export const queryJobs = (
  snapshotId: string,
  page: number,
  signal: AbortSignal,
) =>
  requestJson(
    `/api/v1/jobs/?page=${page}&page_size=20&kind=analysis&snapshot_id=${snapshotId}`,
    (value) =>
      decodePage(value, '/api/v1/jobs/', (item) => {
        const job = parseJob(item);
        if (job.kind !== 'analysis' || job.snapshot_id !== snapshotId)
          throw new ApiError('任务列表归属无效。', 0);
        return job;
      }),
    { signal },
  );
export const retryJob = (
  job: Job,
  archive: File | null,
  key: string,
  signal: AbortSignal,
) => {
  if (job.kind === 'import') {
    if (!archive) throw new ApiError('请重新选择原 ZIP 文件。', 0);
    const body = new FormData();
    body.append('archive', archive);
    return submitBody(
      `/api/v1/jobs/${job.id}/retries/`,
      key,
      parseJob,
      body,
      signal,
    );
  }
  return submitJson(
    `/api/v1/jobs/${job.id}/retries/`,
    key,
    parseJob,
    {},
    signal,
  );
};
export const getCheck = (path: string, signal: AbortSignal) =>
  requestJson(
    path,
    (value): SystemCheck => {
      if (
        !isRecord(value) ||
        typeof value.id !== 'string' ||
        typeof value.job_id !== 'string' ||
        value.check_version !== '1' ||
        value.database !== 'passed' ||
        value.queue !== 'passed' ||
        value.worker !== 'passed' ||
        typeof value.completed_at !== 'string'
      )
        throw new ApiError('检查结果格式无效。', 0);
      return {
        id: value.id,
        job_id: value.job_id,
        check_version: value.check_version,
        database: value.database,
        queue: value.queue,
        worker: value.worker,
        completed_at: value.completed_at,
      };
    },
    { signal },
  );
