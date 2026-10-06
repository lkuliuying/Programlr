import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Empty, Spin, Tag } from 'antd';
import { getJob, listJobs } from './api/jobs-api';
import { Feedback } from '../../shared/components/Feedback';
import type { Job } from '../../shared/api/generated/schema';
import {
  RecordList,
  type RecordColumn,
} from '../../shared/components/RecordList';
import './JobsPage.css';

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
  selectedJobId,
  onResult,
  onSelectJob,
}: {
  active?: boolean;
  onCheck?: (url: string) => void;
  selectedJobId?: string | null;
  onResult?: (job: Job) => void;
  onSelectJob?: (id: string) => void;
} = {}) {
  const search = useSyncExternalStore(subscribe, () => window.location.search);
  const [selectedId, setSelectedId] = useState<string | null>(
    selectedJobId ?? null,
  );
  const [externalId, setExternalId] = useState(selectedJobId);
  const [detailsOpen, setDetailsOpen] = useState(!!selectedJobId);
  if (externalId !== selectedJobId) {
    setExternalId(selectedJobId);
    setSelectedId(selectedJobId ?? null);
    setDetailsOpen(!!selectedJobId);
  }
  const summary = useRef<HTMLElement>(null);
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
  const focusedId = selectedId;
  const detail = useQuery({
    queryKey: ['jobs', 'detail', focusedId],
    queryFn: ({ signal }) => getJob(focusedId!, signal),
    enabled:
      active &&
      !!focusedId &&
      !jobs.data?.results.some((job) => job.id === focusedId),
    retry: false,
  });
  const selectedJob =
    detail.data ?? jobs.data?.results.find((job) => job.id === focusedId);
  const loadedJobId = selectedJob?.id;
  useEffect(() => {
    if (!active || !loadedJobId) return;
    const frame = requestAnimationFrame(() => summary.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [active, loadedJobId]);
  const columns: RecordColumn<Job>[] = [
    {
      key: 'kind',
      title: '任务类型',
      render: (job) => kinds[job.kind],
    },
    {
      key: 'created',
      title: '提交时间',
      width: 190,
      render: (job) => (
        <time dateTime={job.created_at}>
          {new Date(job.created_at).toLocaleString('zh-CN')}
        </time>
      ),
    },
    {
      key: 'status',
      title: '状态',
      width: 100,
      render: (job) => (
        <Tag color={colors[job.status]}>{labels[job.status]}</Tag>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      width: 230,
      render: (job) => (
        <div className="task-record-actions">
          <Button
            type="link"
            aria-label={`查看任务详情：${kinds[job.kind]} ${new Date(job.created_at).toLocaleString('zh-CN')}`}
            aria-expanded={selectedJob?.id === job.id && detailsOpen}
            onClick={() => {
              setSelectedId(job.id);
              setDetailsOpen(true);
              onSelectJob?.(job.id);
              if (selectedId === job.id) summary.current?.focus();
            }}
          >
            查看任务详情
          </Button>
          {job.kind === 'system_check' && job.result_url && onCheck && (
            <Button type="link" onClick={() => onCheck(job.result_url!)}>
              查看检查结果
            </Button>
          )}
        </div>
      ),
    },
  ];
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
      <Feedback error={detail.error} retry={() => void detail.refetch()} />
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
        <RecordList
          label="执行记录清单"
          records={jobs.data.results}
          columns={columns}
          rowKey={(job) => job.id}
          recordTitle={(job) => kinds[job.kind]}
          titleColumnKey="kind"
          selectedKey={selectedJob?.id}
        />
      )}
      {selectedJob && (
        <>
          {selectedJob.status === 'succeeded' &&
            selectedJob.result_url &&
            onResult && (
              <Button onClick={() => onResult(selectedJob)}>
                查看任务结果
              </Button>
            )}
          <details
            className="task-record-details"
            open={detailsOpen}
            onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
          >
            <summary ref={summary}>任务技术详情</summary>
            <dl>
              <dt>完整任务 ID</dt>
              <dd>
                <code>{selectedJob.id}</code>
              </dd>
              <dt>执行阶段</dt>
              <dd>{selectedJob.stage}</dd>
              <dt>更新时间</dt>
              <dd>
                <time dateTime={selectedJob.updated_at}>
                  {new Date(selectedJob.updated_at).toLocaleString('zh-CN')}
                </time>
              </dd>
              <dt>处理量</dt>
              <dd>
                {selectedJob.progress === null
                  ? '未提供处理量'
                  : JSON.stringify(selectedJob.progress)}
              </dd>
              {selectedJob.previous_job_id && (
                <>
                  <dt>重试自任务：</dt>
                  <dd>
                    <code>{selectedJob.previous_job_id}</code>
                  </dd>
                </>
              )}
              {selectedJob.snapshot_id && (
                <>
                  <dt>
                    {selectedJob.kind === 'import'
                      ? '已生成快照：'
                      : selectedJob.kind === 'analysis'
                        ? '分析快照：'
                        : '所属快照：'}
                  </dt>
                  <dd>
                    <code>{selectedJob.snapshot_id}</code>
                  </dd>
                </>
              )}
              {selectedJob.result_url && (
                <>
                  <dt>结果资源</dt>
                  <dd>
                    <code>{selectedJob.result_url}</code>
                  </dd>
                </>
              )}
              {selectedJob.error && (
                <>
                  <dt>失败原因</dt>
                  <dd className="job-error">{selectedJob.error.message}</dd>
                  <dt>错误代码</dt>
                  <dd>
                    <code>{selectedJob.error.code}</code>
                  </dd>
                  <dt>诊断标识</dt>
                  <dd>
                    <code>{selectedJob.error.request_id}</code>
                  </dd>
                  {Object.keys(selectedJob.error.details).length > 0 && (
                    <>
                      <dt>错误明细</dt>
                      <dd>
                        <code>{JSON.stringify(selectedJob.error.details)}</code>
                      </dd>
                    </>
                  )}
                </>
              )}
            </dl>
          </details>
        </>
      )}
    </section>
  );
}
