import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Job } from '../../shared/api/generated/schema';
import { requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import {
  selectFolder,
  type FolderSelection,
} from '../projects/folder-validation';
import { retryFolder } from '../projects/api/mainline-api';
import { getJob, retryJob } from './api/jobs-api';
import type { RetryAction } from './OperationLogsApi';

const states = {
  queued: '等待处理',
  running: '处理中',
  succeeded: '已完成',
  failed: '失败',
};
const kinds: Record<string, string> = {
  import: '导入源码',
  source_scan: '源码扫描',
  analysis: '接口分析',
  explanation: '模型讲解',
  delete: '永久清理',
  system_check: '历史基础检查',
  lab: '历史受控实验',
  snapshot_comparison: '历史快照对比',
};
export function MainlineTask({
  id,
  onJob,
  onResult,
  active = true,
  retryAction,
  retryReason,
}: {
  id: string;
  onJob: (job: Job) => void;
  onResult?: (job: Job) => void;
  active?: boolean;
  retryAction?: RetryAction;
  retryReason?: string;
}) {
  const job = useQuery({
    queryKey: ['jobs', 'detail', id],
    queryFn: ({ signal }) => getJob(id, signal),
    enabled: active,
    refetchInterval: (query) =>
      active &&
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.status)
        ? 1500
        : false,
  });
  const [historyOpen, setHistoryOpen] = useState(false);
  const data = job.data;
  const removed =
    !!data && 'result_deleted' in data && data.result_deleted === true;
  const historical =
    !!data &&
    ['system_check', 'lab', 'snapshot_comparison'].includes(data.kind);
  const history = useQuery({
    queryKey: ['jobs', 'historic-result', id],
    queryFn: ({ signal }) =>
      requestJson(data!.result_url!, v.object, { signal }),
    enabled: active && historyOpen && !!data?.result_url && !removed,
  });
  return (
    <section
      className="surface mainline-task"
      aria-label="当前操作"
      aria-live="polite"
    >
      <h3>
        {data
          ? `${kinds[data.kind] ?? data.kind} · ${states[data.status]}`
          : '读取操作状态…'}
      </h3>
      <small>任务 {id}</small>
      <Feedback error={job.error} retry={() => void job.refetch()} />
      {data && (
        <>
          <p>阶段：{data.stage}</p>
          {data.error && (
            <p role="alert">
              {data.error.message} <code>{data.error.code}</code>
            </p>
          )}
          {removed && <p>结果已删除，保留本次操作结论与任务摘要。</p>}
          {historical && (
            <p>此功能已退役。历史结果保持只读，不能继续执行或重试。</p>
          )}
          {data.status === 'succeeded' && !removed && data.result_url && (
            <Button
              onClick={() =>
                historical || !onResult
                  ? setHistoryOpen(!historyOpen)
                  : onResult(data)
              }
            >
              {historyOpen ? '收起历史结果' : '查看结果'}
            </Button>
          )}
          {data.status === 'failed' &&
            !historical &&
            !removed &&
            (retryAction === 'none' ? (
              <p>{retryReason ?? '此任务当前不能重试。'}</p>
            ) : data.kind === 'explanation' ? (
              <p>请返回原讲解预览重新确认后显式重试。</p>
            ) : (
              <MainlineRetry key={data.id} job={data} onJob={onJob} />
            ))}
        </>
      )}
      {historyOpen && (
        <>
          <Feedback error={history.error} />
          {history.data && (
            <pre className="historic-result">
              {JSON.stringify(history.data, null, 2)}
            </pre>
          )}
        </>
      )}
    </section>
  );
}
function MainlineRetry({
  job,
  onJob,
}: {
  job: Job;
  onJob: (job: Job) => void;
}) {
  const [archive, setArchive] = useState<File | null>(null),
    [folder, setFolder] = useState<FolderSelection | null>(null),
    [error, setError] = useState<Error | null>(null);
  const sourceKind = 'source_kind' in job ? job.source_kind : '';
  const operation = useIdempotentOperation<File | FolderSelection | null, Job>(
    `mainline-retry.${job.id}`,
    (input) =>
      input instanceof File
        ? input
        : input
          ? new Blob(
              input.entries.flatMap(({ path, file }) => [
                JSON.stringify(path),
                file,
              ]),
            )
          : '{}',
    (input, key, signal) =>
      input && !(input instanceof File)
        ? retryFolder(job.id, input, key, signal)
        : retryJob(job, input, key, signal),
    onJob,
  );
  return (
    <form
      className="workspace-form"
      onSubmit={(event) => {
        event.preventDefault();
        operation.start(sourceKind === 'folder' ? folder : archive);
      }}
    >
      {job.kind === 'import' &&
        (sourceKind === 'folder' ? (
          <label>
            重新选择原目录
            <input
              type="file"
              multiple
              ref={(node) => node?.setAttribute('webkitdirectory', '')}
              required
              onChange={(event) => {
                try {
                  setFolder(selectFolder([...(event.target.files ?? [])]));
                  setError(null);
                } catch (error) {
                  setFolder(null);
                  setError(
                    error instanceof Error ? error : new Error('目录无效。'),
                  );
                }
              }}
            />
          </label>
        ) : (
          <label>
            重新选择原 ZIP
            <input
              type="file"
              required
              accept=".zip"
              onChange={(event) => setArchive(event.target.files?.[0] ?? null)}
            />
          </label>
        ))}
      <Button
        htmlType="submit"
        loading={operation.isPending}
        disabled={
          !!error ||
          (job.kind === 'import' &&
            !(sourceKind === 'folder' ? folder : archive))
        }
      >
        {String(job.kind) === 'delete'
          ? '继续清理'
          : operation.pending
            ? '恢复本次重试'
            : '显式重试'}
      </Button>
      <Feedback error={error ?? operation.error} />
    </form>
  );
}
