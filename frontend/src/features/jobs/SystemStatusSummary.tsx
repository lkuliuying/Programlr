import { useQuery } from '@tanstack/react-query';
import { Icon } from '../../shared/components/Icon';
import { getCheck, listJobs } from './api/jobs-api';
export function SystemStatusSummary({
  onOpen,
  active = true,
}: {
  onOpen: () => void;
  active?: boolean;
}) {
  const jobs = useQuery({
    queryKey: ['jobs', 1],
    queryFn: ({ signal }) => listJobs(1, signal),
    enabled: active,
    refetchInterval: (query) =>
      active &&
      query.state.data?.results.some(
        (job) =>
          job.kind === 'system_check' &&
          ['queued', 'running'].includes(job.status),
      )
        ? 1500
        : false,
    refetchIntervalInBackground: false,
  });
  const latest = jobs.data?.results.find((job) => job.kind === 'system_check');
  const result = useQuery({
    queryKey: ['system-check', latest?.result_url ?? null],
    queryFn: ({ signal }) => getCheck(latest!.result_url!, signal),
    enabled: active && latest?.status === 'succeeded' && !!latest.result_url,
  });
  const label = result.data
    ? '通过'
    : jobs.error || result.error
      ? '不可读取'
      : latest?.status === 'failed'
        ? '失败'
        : latest?.status === 'running'
          ? '检查中'
          : latest?.status === 'queued'
            ? '排队中'
            : latest?.status === 'succeeded'
              ? '读取中'
              : '未检查';
  return (
    <div className="system-status-summary">
      <button className="status-heading" onClick={onOpen}>
        <Icon name="cube" />
        <span>
          本地基础检查
          <small>
            {result.data
              ? new Date(result.data.completed_at).toLocaleString('zh-CN')
              : '已加载任务范围 · 需显式检查'}
          </small>
        </span>
      </button>
      {['数据库', '队列', 'Worker'].map((name) => (
        <span className="service-chip" key={name}>
          <strong>{name}</strong>
          <small className={result.data ? 'accent-text' : 'muted'}>
            {label}
          </small>
        </span>
      ))}
      <span className="sr-only">
        检查结果只代表该次检查，不保证服务持续可用。
      </span>
    </div>
  );
}
