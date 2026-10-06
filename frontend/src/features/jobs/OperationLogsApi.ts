import { ApiError } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import type {
  OperationLog,
  OperationStatistics,
  RetryActionEnum,
} from '../../shared/api/generated/schema';
import { parseJob } from './api/jobs-api';

export type RetryAction = RetryActionEnum;

export function parseOperationLog(raw: unknown): OperationLog {
  const item = v.object(raw);
  return {
    id: v.uuid(item.id),
    display_id: v.integer(item.display_id, 1),
    operation: v.text(item.operation),
    result: v.text(item.result),
    request_id: v.text(item.request_id, 64),
    source_kind: v.text(item.source_kind, 10),
    job_id: v.nullable(item.job_id, v.uuid),
    project_id: v.nullable(item.project_id, v.uuid),
    project_name: v.text(item.project_name, 200),
    object_name: v.text(item.object_name, 200),
    snapshot_id: v.nullable(item.snapshot_id, v.uuid),
    job: v.nullable(item.job, parseJob),
    error_code: v.text(item.error_code, 80),
    events: v.list(item.events, v.object),
    result_deleted: v.boolean(item.result_deleted),
    started_at: v.date(item.started_at),
    ended_at: v.nullable(item.ended_at, v.date),
    created_at: v.date(item.created_at),
    updated_at: v.date(item.updated_at),
    retry_action: v.oneOf(item.retry_action, [
      'none',
      'direct',
      'upload_zip',
      'select_folder',
      'reconfirm_explanation',
      'continue_cleanup',
    ]),
    retry_reason: v.text(item.retry_reason, 500),
    project_available: v.boolean(item.project_available),
  };
}

export const operationLabels: Record<string, string> = {
  import: '源码导入',
  source_scan: '源码扫描',
  analysis: '接口分析',
  explanation: '模型讲解',
  delete: '永久删除',
  delete_project: '删除项目',
  delete_snapshot: '删除快照',
  retry: '任务重试',
  lab: '历史实验',
  snapshot_comparison: '历史对比',
  system_check: '历史检查',
};
export const outcomeLabels: Record<string, string> = {
  submitted: '已提交',
  accepted: '已接收',
  running: '处理中',
  succeeded: '成功',
  failed: '失败',
  rejected: '前置拒绝',
  replayed: '幂等重放',
};

export function parseOperationStatistics(raw: unknown): OperationStatistics {
  const item = v.object(raw);
  const rate = (value: unknown) => {
    if (
      typeof value !== 'number' ||
      !Number.isFinite(value) ||
      value < 0 ||
      value > 100
    )
      return v.invalid();
    return value;
  };
  const window = (raw: unknown) => {
    const value = v.object(raw);
    return { start: v.date(value.start), end: v.date(value.end) };
  };
  return {
    as_of: v.date(item.as_of),
    count: v.integer(item.count),
    failed_count: v.integer(item.failed_count),
    active_count: v.integer(item.active_count),
    retryable_count: v.integer(item.retryable_count),
    recent_success_rate: v.nullable(item.recent_success_rate, rate),
    previous_success_rate: v.nullable(item.previous_success_rate, rate),
    success_rate_change_pp: v.nullable(item.success_rate_change_pp, (value) => {
      if (
        typeof value !== 'number' ||
        !Number.isFinite(value) ||
        Math.abs(value) > 100
      )
        return v.invalid();
      return value;
    }),
    recent_window: window(item.recent_window),
    previous_window: window(item.previous_window),
    trend: v.list(
      item.trend,
      (raw) => {
        const value = v.object(raw);
        return {
          ...window(value),
          count: v.integer(value.count),
          failed_count: v.integer(value.failed_count),
        };
      },
      7,
    ),
  };
}

export async function downloadOperationLogs(
  query: URLSearchParams,
  signal: AbortSignal,
): Promise<Blob> {
  const filters = new URLSearchParams(query);
  filters.delete('page');
  filters.delete('page_size');
  let response: Response;
  try {
    response = await fetch('/api/v1/operation-logs/export/?' + filters, {
      signal: AbortSignal.any([signal, AbortSignal.timeout(30000)]),
      credentials: 'same-origin',
      redirect: 'error',
      cache: 'no-store',
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new ApiError('日志导出连接失败，请稍后重试。', 0);
  }
  if (!response.ok) {
    let message = '日志导出失败，请重试。';
    try {
      const body = v.object(await response.json());
      message = v.text(body.message, 2000);
    } catch {
      /* 错误响应不是契约对象时保留通用提示。 */
    }
    throw new ApiError(message, response.status);
  }
  if (
    !response.headers.get('Content-Type')?.startsWith('text/csv') ||
    !response.body
  )
    throw new ApiError('日志导出响应格式无效。', response.status);
  const reader = response.body.getReader();
  const parts: Uint8Array<ArrayBuffer>[] = [];
  let size = 0;
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      size += chunk.value.byteLength;
      if (size > 10 * 1024 * 1024) {
        await reader.cancel();
        throw new ApiError('日志导出超过 10 MiB，请缩小筛选范围。', 413);
      }
      parts.push(new Uint8Array(chunk.value));
    }
  } catch (error) {
    if (signal.aborted || error instanceof ApiError) throw error;
    throw new ApiError('导出数据接收中断，请重试。', 0);
  } finally {
    reader.releaseLock();
  }
  return new Blob(parts, { type: 'text/csv;charset=utf-8' });
}
