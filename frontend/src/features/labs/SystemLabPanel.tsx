import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  Job,
  SystemLab,
  SystemLabInputRequest,
  SystemLabRun,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { JobStatus } from '../jobs';
import type { LabSelection } from './api/labs-api';
import * as api from './api/system-labs-api';

const active = (run: SystemLabRun | null | undefined) =>
  !!run && ['queued', 'running'].includes(run.job.status);
const states = {
  queued: '排队中',
  running: '执行中',
  succeeded: '真实观测已保存',
  failed: '实验失败',
};
export function SystemLabPanel({
  selected,
  runId,
  jobId,
  onRun,
  onJob,
}: {
  selected: LabSelection;
  runId: string | null;
  jobId: string | null;
  onRun: (id: string) => void;
  onJob: (id: string) => void;
}) {
  const [page, setPage] = useState(1);
  const labs = useQuery({
    queryKey: ['system-labs', 'definitions', selected],
    queryFn: ({ signal }) => api.listSystemLabs(selected, signal),
  });
  const history = useQuery({
    queryKey: ['system-labs', 'history', selected, page, jobId],
    queryFn: ({ signal }) => api.listSystemRuns(selected, page, signal),
    refetchInterval: (query) =>
      query.state.data?.results.some(active) ? 1500 : false,
  });
  const detail = useQuery({
    queryKey: ['system-labs', 'run', selected, runId],
    queryFn: ({ signal }) => api.getSystemRun(runId!, selected, signal),
    enabled: !!runId,
    refetchInterval: (query) => (active(query.state.data) ? 1500 : false),
  });
  const jobRun = useQuery({
    queryKey: ['system-labs', 'job-run', selected, jobId],
    queryFn: ({ signal }) => api.getSystemRunForJob(selected, jobId!, signal),
    enabled: !!jobId && !runId,
    refetchInterval: (query) => (active(query.state.data) ? 1500 : false),
  });
  const run = runId ? detail.data : jobRun.data;
  return (
    <section aria-label="网络与进程实验">
      <h3>网络与进程：预测，再观测</h3>
      <p>固定程序在独立运行环境执行，导入源码保持只读。</p>
      <Feedback
        error={labs.error ?? history.error ?? detail.error ?? jobRun.error}
        retry={() => {
          void labs.refetch();
          void history.refetch();
          if (runId) void detail.refetch();
          else if (jobId) void jobRun.refetch();
        }}
      />
      {labs.isPending && <p role="status">读取固定系统实验…</p>}
      {labs.data?.results.map((lab) => (
        <article key={lab.id}>
          <h4>{lab.title}</h4>
          <p>{lab.description}</p>
          {lab.applicable ? (
            <SystemPredictionForm
              key={`${lab.id}.${lab.version}.${lab.program_digest}`}
              lab={lab}
              selected={selected}
              onJob={onJob}
            />
          ) : (
            <p role="note">{lab.applicability_reason}</p>
          )}
        </article>
      ))}
      {run && <SystemResult run={run} onJob={onJob} onRun={onRun} />}
      <h4>系统实验历史</h4>
      {history.data?.count === 0 && <p>尚无网络或进程实验。</p>}
      <ul>
        {history.data?.results.map((item) => (
          <li key={item.id}>
            <button type="button" onClick={() => onRun(item.id)}>
              {item.definition.title} · {states[item.job.status]} ·{' '}
              {new Date(item.created_at).toLocaleString()}
            </button>
          </li>
        ))}
      </ul>
      {history.data && (
        <PageControls
          page={page}
          previous={history.data.previous}
          next={history.data.next}
          onPage={setPage}
        />
      )}
    </section>
  );
}
function SystemPredictionForm({
  lab,
  selected,
  onJob,
}: {
  lab: SystemLab;
  selected: LabSelection;
  onJob: (id: string) => void;
}) {
  const [answers, setAnswers] = useState({ first: '', second: '' }),
    cache = useQueryClient();
  const operation = useIdempotentOperation<
    SystemLabInputRequest & { lab_id: string },
    Job
  >(
    `system-lab.${selected.analysis}.${selected.endpoint}.${lab.id}.${lab.version}`,
    JSON.stringify,
    api.submitSystemRun,
    (job) => {
      void cache.invalidateQueries({ queryKey: ['system-labs', 'history'] });
      onJob(job.id);
    },
    onJob,
  );
  return (
    <form
      className="lab-predictions"
      onSubmit={(event) => {
        event.preventDefault();
        if (
          ['first', 'second'].every((key) =>
            ['yes', 'no'].includes(answers[key as 'first' | 'second']),
          )
        )
          operation.start({
            lab_id: lab.id,
            lab_version: lab.version,
            snapshot_id: selected.snapshot,
            analysis_id: selected.analysis,
            endpoint_index: selected.endpoint,
            predictions: {
              first: answers.first === 'yes',
              second: answers.second === 'yes',
            },
          });
      }}
    >
      {lab.cases.map((item) => {
        const key = item.id === 'first' ? 'first' : 'second';
        return (
          <label key={key}>
            {item.prediction_label}
            <select
              required
              value={answers[key]}
              onChange={(event) =>
                setAnswers({ ...answers, [key]: event.target.value })
              }
            >
              <option value="">请选择预测</option>
              <option value="yes">能</option>
              <option value="no">不能</option>
            </select>
          </label>
        );
      })}
      <Button htmlType="submit" loading={operation.isPending}>
        {operation.pending
          ? `恢复${lab.title}提交`
          : `提交预测并运行${lab.title}`}
      </Button>
      <Feedback error={operation.error} />
    </form>
  );
}
function SystemResult({
  run,
  onJob,
  onRun,
}: {
  run: SystemLabRun;
  onJob: (id: string) => void;
  onRun: (id: string) => void;
}) {
  return (
    <section className="lab-result" aria-label="系统实验观测">
      <h4>
        {run.definition.title} · {states[run.job.status]}
      </h4>
      <p>
        可信示例 {run.definition.example_version} · 运行 {run.id}
      </p>
      <JobStatus
        id={run.job.id}
        snapshotId={null}
        onSelect={onJob}
        onResult={() => onRun(run.id)}
      />
      {run.observations.length === 0 && <p>尚未保存探测结果；没有预设观测。</p>}
      {run.observations.map((item) => (
        <article key={item.case_id}>
          <h5>
            {
              run.definition.cases.find((entry) => entry.id === item.case_id)
                ?.title
            }
          </h5>
          <p>你的预测：{run.predictions[item.case_id] ? '能' : '不能'}</p>
          {run.lab_id === 'container-network' ? (
            <>
              <p>
                实际目标：{item.hostname ?? '未取得'}；DNS 地址：
                {item.addresses.join('、') || '未取得'}
              </p>
              <p>
                实际 TCP：
                {item.connected === true
                  ? '连接成功'
                  : item.connected === false
                    ? '连接未成功'
                    : '未取得结果'}
                {item.error_code && ` · ${item.error_code}`}
              </p>
            </>
          ) : (
            <>
              <p>
                PID：{item.pid ?? '未创建'}；返回码：
                {item.return_code ?? '未取得'}；
                {item.timed_out ? '发生超时并尝试终止' : '未发生等待超时'}；
                {item.reaped === true
                  ? '已 wait 回收'
                  : item.reaped === false
                    ? '回收未确认'
                    : '未创建子进程'}
              </p>
              <pre aria-label="实际子进程输出">
                {item.stdout || '未取得输出'}
              </pre>
              {item.error_code && <p>{item.error_code}</p>}
            </>
          )}
          <small>
            实际耗时 {item.elapsed_ms} ms ·{' '}
            {new Date(item.observed_at).toLocaleString()}
          </small>
        </article>
      ))}
      <p role="status">
        清理状态：
        {run.cleanup.status === 'completed'
          ? '已确认释放本次子进程资源'
          : run.cleanup.status === 'unconfirmed'
            ? '回收未确认，不能视为成功'
            : '尚无清理确认'}
      </p>
    </section>
  );
}
