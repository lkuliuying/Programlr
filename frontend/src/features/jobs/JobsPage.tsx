import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Empty, Spin, Tag } from 'antd';
import { getCheck, listJobs, submitCheck } from './api/jobs-api';
import { ApiError } from '../../shared/api/client';

const pendingKeyName = 'learning-lab.pending-system-check';
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

export function JobsPage({
  embedded = false,
  active = true,
}: { embedded?: boolean; active?: boolean } = {}) {
  const queryClient = useQueryClient();
  const [pendingKey, setPendingKey] = useState(() =>
    sessionStorage.getItem(pendingKeyName),
  );
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const rawPage =
    new URLSearchParams(window.location.search).get('page') ?? '1';
  const page =
    /^\d+$/.test(rawPage) &&
    Number(rawPage) > 0 &&
    Number.isSafeInteger(Number(rawPage))
      ? Number(rawPage)
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
  const result = useQuery({
    queryKey: ['system-check', resultUrl],
    queryFn: ({ signal }) => getCheck(resultUrl ?? '', signal),
    enabled: active && resultUrl !== null,
  });
  const submit = useMutation({
    mutationFn: submitCheck,
    onSuccess: () => {
      sessionStorage.removeItem(pendingKeyName);
      setPendingKey(null);
      if (page !== 1) window.location.assign('/');
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
  function startCheck() {
    const key = pendingKey ?? crypto.randomUUID();
    sessionStorage.setItem(pendingKeyName, key);
    setPendingKey(key);
    submit.mutate(key);
  }
  const error = submit.error ?? jobs.error ?? result.error;
  return (
    <div className="workbench">
      {!embedded && (
        <header className="topbar">
          <span className="brand-mark" aria-hidden="true">
            解
          </span>
          <strong>项目解读实验室</strong>
          <span className="local-label">本地工作台</span>
        </header>
      )}
      <section className="jobs-body">
        <div className="page-heading">
          <div>
            {!embedded && <p className="eyebrow">工作台 / 基础检查</p>}
            {embedded ? (
              <h2>基础检查与任务历史</h2>
            ) : (
              <h1>
                让每次执行
                <br />
                <em>都有迹可循。</em>
              </h1>
            )}
            <p className="intro">
              提交一次基础检查，确认任务能够保存、执行并留下结果。
              <br />
              记录保存在本地，刷新页面后仍可查看。
            </p>
          </div>
          <div className="action-panel">
            <span className="section-index">01 / 基础链路</span>
            <p>检查本地任务服务</p>
            <Button
              type="primary"
              size="large"
              loading={submit.isPending}
              onClick={startCheck}
            >
              {pendingKey ? '恢复这次提交' : '开始基础检查'}
            </Button>
            <small>只执行固定检查，不读取项目源码。</small>
          </div>
        </div>
        {error && (
          <Alert
            type="error"
            showIcon
            title={error.message}
            description={
              error instanceof ApiError && error.requestId
                ? `请求标识：${error.requestId}`
                : '请确认本地服务已启动；未知提交可用原操作标识恢复。'
            }
          />
        )}
        {pendingKey && !submit.isPending && (
          <p role="status" className="pending-note">
            有一次提交尚待确认。恢复会使用原操作标识，避免重复创建。
          </p>
        )}
        <section aria-labelledby="history-title" className="history">
          <div className="section-heading">
            <div>
              <span className="section-index">执行记录</span>
              <h2 id="history-title">
                任务历史 <span>{jobs.data?.count ?? '—'}</span>
              </h2>
            </div>
            <Button
              onClick={() => void jobs.refetch()}
              loading={jobs.isFetching}
            >
              刷新记录
            </Button>
          </div>
          {jobs.isPending ? (
            <div className="empty-state">
              <Spin aria-label="正在读取任务" />
            </div>
          ) : !jobs.data ? (
            <p>尚未取得任务记录。</p>
          ) : jobs.data.results.length === 0 ? (
            <div className="empty-state">
              <Empty description="还没有任务。开始一次基础检查，建立第一条记录。" />
            </div>
          ) : (
            <ol className="job-list">
              {jobs.data.results.map((job) => (
                <li key={job.id}>
                  <div className="job-main">
                    <span className="job-label">
                      {job.kind === 'import'
                        ? '项目导入'
                        : job.kind === 'analysis'
                          ? '源码分析'
                          : job.kind === 'explanation'
                            ? '源码讲解'
                            : '基础链路检查'}
                    </span>
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
                  {job.kind === 'system_check' && job.result_url && (
                    <Button
                      type="link"
                      onClick={() => setResultUrl(job.result_url)}
                    >
                      查看检查结果
                    </Button>
                  )}
                </li>
              ))}
            </ol>
          )}
          {jobs.data && (
            <nav aria-label="任务历史分页" className="pagination">
              <a
                aria-disabled={!jobs.data.previous}
                href={
                  jobs.data.previous ? `?view=jobs&page=${page - 1}` : undefined
                }
              >
                上一页
              </a>
              <span>第 {page} 页</span>
              <a
                aria-disabled={!jobs.data.next}
                href={
                  jobs.data.next ? `?view=jobs&page=${page + 1}` : undefined
                }
              >
                下一页
              </a>
            </nav>
          )}
        </section>
        {resultUrl && (
          <section className="result-panel" aria-live="polite">
            <h2>本次检查结果</h2>
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
            <Button onClick={() => setResultUrl(null)}>关闭结果</Button>
          </section>
        )}
        <footer>
          项目解读实验室 <span>本地单用户 · 基础任务工作台</span>
        </footer>
      </section>
    </div>
  );
}
