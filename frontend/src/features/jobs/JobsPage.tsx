import { useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Empty, Spin, Tag } from 'antd';
import { listJobs } from './api/jobs-api';
import { Feedback } from '../../shared/components/Feedback';

const labels = {
  queued: '排队中',
  running: '执行中',
  succeeded: '已完成',
  failed: '失败',
};
const colors = {
  queued: 'default',
  running: 'processing',
  succeeded: 'success',
  failed: 'error',
};
const kinds: Record<string, string> = {
  import: '项目导入',
  analysis: '源码分析',
  explanation: '源码讲解',
  lab: '受控实验',
  snapshot_comparison: '快照对比',
  system_check: '基础链路检查',
};
function subscribe(callback: () => void) {
  window.addEventListener('popstate', callback);
  return () => window.removeEventListener('popstate', callback);
}
export function JobsPage({
  active = true,
  onCheck,
}: { active?: boolean; onCheck?: (url: string) => void } = {}) {
  const search = useSyncExternalStore(subscribe, () => window.location.search);
  const raw = new URLSearchParams(search).get('page') ?? '1';
  const page =
    /^\d+$/.test(raw) && Number.isSafeInteger(Number(raw)) && Number(raw) > 0
      ? Number(raw)
      : 1;
  const jobs = useQuery({
    queryKey: ['jobs', page],
    queryFn: ({ signal }) => listJobs(page, signal),
    enabled: active,
    refetchInterval: (query) =>
      active &&
      query.state.data?.results.some(
        (job) => job.status === 'queued' || job.status === 'running',
      )
        ? 2000
        : false,
    refetchIntervalInBackground: false,
  });
  function move(next: number) {
    const params = new URLSearchParams(window.location.search);
    params.delete('view');
    params.set('section', 'jobs');
    params.set('page', String(next));
    window.history.pushState({}, '', '?' + params);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }
  return (
    <section aria-label="任务记录" className="task-history">
      <div className="section-heading">
        <h2>
          执行记录 <span>{jobs.data?.count ?? '—'}</span>
        </h2>
        <Button onClick={() => void jobs.refetch()} loading={jobs.isFetching}>
          刷新记录
        </Button>
      </div>
      <p className="muted">记录保存在本地。基础链路检查请前往系统状态。</p>
      <Feedback error={jobs.error} retry={() => void jobs.refetch()} />
      {jobs.data && (
        <nav aria-label="任务历史分页" className="workspace-pagination">
          <button disabled={!jobs.data.previous} onClick={() => move(page - 1)}>
            上一批记录
          </button>
          <span>第 {page} 批 · 每批最多 20 条</span>
          <button disabled={!jobs.data.next} onClick={() => move(page + 1)}>
            下一批记录
          </button>
        </nav>
      )}
      {jobs.isPending ? (
        <Spin aria-label="正在读取任务" />
      ) : !jobs.data ? (
        <p>尚未取得任务记录。</p>
      ) : jobs.data.results.length === 0 ? (
        <Empty description="还没有任务。可在系统状态开始基础检查，或在项目导入中导入源码。" />
      ) : (
        <ol className="job-list">
          {jobs.data.results.map((job) => (
            <li key={job.id} data-page-keep>
              <div className="job-main">
                <span className="job-label">{kinds[job.kind]}</span>
                <Tag color={colors[job.status]}>{labels[job.status]}</Tag>
                <time dateTime={job.created_at}>
                  {new Date(job.created_at).toLocaleString('zh-CN')}
                </time>
              </div>
              <code>{job.id}</code>
              {job.error && (
                <p className="job-error">
                  {job.error.message}
                  <small>诊断标识：{job.error.request_id}</small>
                </p>
              )}
              {job.previous_job_id && (
                <p>
                  重试自任务：<code>{job.previous_job_id}</code>
                </p>
              )}
              {job.kind === 'import' && job.snapshot_id && (
                <p>
                  已生成快照：<code>{job.snapshot_id}</code>
                </p>
              )}
              {job.kind === 'analysis' && job.snapshot_id && (
                <p>
                  分析快照：<code>{job.snapshot_id}</code>
                </p>
              )}
              {job.kind === 'system_check' && job.result_url && onCheck && (
                <Button type="link" onClick={() => onCheck(job.result_url!)}>
                  查看检查结果
                </Button>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
