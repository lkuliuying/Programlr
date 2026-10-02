import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Job } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { getJob, retryJob } from './api/jobs-api';

const states = {
  queued: '等待处理',
  running: '处理中',
  succeeded: '已完成',
  failed: '失败',
};
export function JobStatus({
  id,
  snapshotId,
  onSelect,
  onResult,
}: {
  id: string;
  snapshotId: string | null;
  onSelect: (id: string) => void;
  onResult: (job: Job) => void;
}) {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ['jobs', 'detail', id],
    queryFn: ({ signal }) => getJob(id, signal),
    refetchInterval: (query) =>
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.status)
        ? 1500
        : false,
  });
  const job = query.data;
  useEffect(() => {
    if (job?.status === 'succeeded') {
      void cache.invalidateQueries({ queryKey: ['projects', 'snapshots'] });
      void cache.invalidateQueries({ queryKey: ['jobs', 'history'] });
    }
  }, [job?.status, cache]);
  if (
    job &&
    ['analysis', 'explanation'].includes(job.kind) &&
    job.snapshot_id !== snapshotId
  )
    return <p role="alert">任务不属于当前快照，请重新选择。</p>;
  return (
    <section className="workspace-job" aria-label="当前任务" aria-live="polite">
      <h3>当前任务 {job && states[job.status]}</h3>
      <code>{id}</code>
      {query.isPending && <p role="status">正在查询任务…</p>}
      <Feedback
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {job?.error && (
        <p role="alert">
          {job.error.message}
          <br />
          <small>请求标识：{job.error.request_id}</small>
        </p>
      )}
      {job?.kind === 'explanation' && job.status === 'failed' && (
        <p>请在原讲解预览中重新确认后重试；可能重复计费。</p>
      )}
      {job?.status === 'succeeded' && (
        <Button onClick={() => onResult(job)}>查看任务结果</Button>
      )}
      {job?.status === 'failed' && job.kind !== 'explanation' && (
        <RetryForm key={job.id} job={job} onSelect={onSelect} />
      )}
    </section>
  );
}
function RetryForm({
  job,
  onSelect,
}: {
  job: Job;
  onSelect: (id: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const operation = useIdempotentOperation<File | null, Job>(
    `retry.${job.id}`,
    (file) => file ?? '{}',
    (file, key, signal) => retryJob(job, file, key, signal),
    (result) => onSelect(result.id),
    onSelect,
  );
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        operation.start(file);
      }}
    >
      {job.kind === 'import' && (
        <label>
          重新选择原 ZIP
          <input
            type="file"
            accept=".zip"
            required
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
      )}
      <Button htmlType="submit" loading={operation.isPending}>
        {operation.pending ? '恢复本次重试' : '创建重试任务'}
      </Button>
      <Feedback error={operation.error} />
    </form>
  );
}
