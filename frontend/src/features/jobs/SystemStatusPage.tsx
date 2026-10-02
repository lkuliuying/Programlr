import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import { Feedback } from '../../shared/components/Feedback';
import { getCheck, getJob, submitCheck } from './api/jobs-api';
import { SystemStatusSummary } from './SystemStatusSummary';

const pendingKeyName = 'learning-lab.pending-system-check';
export function SystemStatusPage({
  active = true,
  selectedCheck = null,
  onHistory,
}: {
  active?: boolean;
  selectedCheck?: { url: string } | null;
  onHistory: () => void;
}) {
  const cache = useQueryClient();
  const [pendingKey, setPendingKey] = useState(() =>
    sessionStorage.getItem(pendingKeyName),
  );
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [historySelection, setHistorySelection] = useState(selectedCheck);
  if (historySelection !== selectedCheck) {
    setHistorySelection(selectedCheck);
    setSubmitted(null);
  }
  const job = useQuery({
    queryKey: ['jobs', 'detail', submitted],
    queryFn: ({ signal }) => getJob(submitted!, signal),
    enabled: active && !!submitted,
    refetchInterval: (query) =>
      active && ['queued', 'running'].includes(query.state.data?.status ?? '')
        ? 1500
        : false,
    refetchIntervalInBackground: false,
  });
  const resultUrl = submitted ? job.data?.result_url : selectedCheck?.url;
  const result = useQuery({
    queryKey: ['system-check', resultUrl],
    queryFn: ({ signal }) => getCheck(resultUrl!, signal),
    enabled: active && !!resultUrl,
  });
  const submit = useMutation({
    mutationFn: submitCheck,
    onSuccess: (job) => {
      sessionStorage.removeItem(pendingKeyName);
      setPendingKey(null);
      setSubmitted(job.id);
      cache.setQueryData(['jobs', 'detail', job.id], job);
      void cache.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: () => {
      void cache.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
  const running =
    submit.isPending || ['queued', 'running'].includes(job.data?.status ?? '');
  return (
    <div className="system-status-page">
      <SystemStatusSummary active={active} onOpen={onHistory} />
      <section className="surface module-summary" aria-label="本地基础检查">
        <h2>检查本地任务服务</h2>
        <p>显式提交一次固定检查，核对数据库写入、队列交付和 Worker 执行。</p>
        <p className="muted">
          只执行固定检查，不读取项目源码。结果仅代表该次检查，不保证服务持续可用。
        </p>
        <div className="module-actions">
          <Button
            type="primary"
            loading={submit.isPending}
            disabled={running}
            onClick={() => {
              const key = pendingKey ?? crypto.randomUUID();
              sessionStorage.setItem(pendingKeyName, key);
              setPendingKey(key);
              submit.mutate(key);
            }}
          >
            {pendingKey ? '恢复这次提交' : '开始基础检查'}
          </Button>
          <button onClick={onHistory}>查看任务历史</button>
        </div>
        <Feedback
          error={submit.error ?? job.error ?? result.error}
          retry={
            job.error
              ? () => void job.refetch()
              : result.error
                ? () => void result.refetch()
                : undefined
          }
        />
        {pendingKey && !submit.isPending && (
          <p role="status" className="pending-note">
            有一次提交尚待确认。恢复会使用原操作标识，避免重复创建。
          </p>
        )}
        {job.data && (
          <p role="status">
            本次检查：
            {
              {
                queued: '排队中',
                running: '执行中',
                succeeded: '已完成',
                failed: '失败',
              }[job.data.status]
            }
          </p>
        )}
        {job.data?.error && <p role="alert">{job.data.error.message}</p>}
      </section>
      {resultUrl && (
        <section
          className="result-panel"
          aria-label="检查结果"
          aria-live="polite"
        >
          <h2>{submitted ? '本次检查结果' : '历史检查结果'}</h2>
          {result.isPending ? (
            <p>正在读取…</p>
          ) : result.data ? (
            <>
              <p>任务已保存，队列已交付，Worker 已完成结果写入。</p>
              <p>
                完成于{' '}
                {new Date(result.data.completed_at).toLocaleString('zh-CN')}
              </p>
              <small>结果仅代表该次检查，不保证服务持续可用。</small>
            </>
          ) : (
            <p>检查结果暂不可读。</p>
          )}
        </section>
      )}
    </div>
  );
}
