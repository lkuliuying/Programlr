import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  Job,
  Lab,
  LabInputRequest,
  LabRun,
  PredictionsRequest,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { JobStatus } from '../jobs';
import {
  cases,
  getLab,
  getRun,
  getRunForJob,
  listRuns,
  submitRun,
  type LabSelection,
} from './api/labs-api';
import { SystemLabPanel } from './SystemLabPanel';

const states = {
  queued: '排队中',
  running: '执行中',
  succeeded: '完整观测已保存',
  failed: '实验失败',
};
export function LabPanel({
  selected,
  runId,
  jobId,
  onRun,
  onJob,
  systemRunId = null,
  onSystemRun = () => {},
}: {
  selected: LabSelection;
  runId: string | null;
  jobId: string | null;
  onRun: (id: string) => void;
  onJob: (id: string) => void;
  systemRunId?: string | null;
  onSystemRun?: (id: string) => void;
}) {
  const [page, setPage] = useState(1);
  const lab = useQuery({
    queryKey: ['labs', 'definition', selected],
    queryFn: ({ signal }) => getLab(selected, signal),
  });
  const history = useQuery({
    queryKey: ['labs', 'history', selected, page, jobId],
    queryFn: ({ signal }) => listRuns(selected, page, signal),
    refetchInterval: (query) =>
      query.state.data?.results.some((run) =>
        ['queued', 'running'].includes(run.job.status),
      )
        ? 1500
        : false,
  });
  const detail = useQuery({
    queryKey: ['labs', 'run', selected, runId],
    queryFn: ({ signal }) => getRun(runId!, selected, signal),
    enabled: !!runId,
    refetchInterval: (query) =>
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.job.status)
        ? 1500
        : false,
  });
  const jobRun = useQuery({
    queryKey: ['labs', 'job-run', selected, jobId],
    queryFn: ({ signal }) => getRunForJob(selected, jobId!, signal),
    enabled: !!jobId && !runId,
    refetchInterval: (query) =>
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.job.status)
        ? 1500
        : false,
  });
  const run = runId ? detail.data : jobRun.data;
  return (
    <section aria-label="内置实验">
      <h2>预测，再看真实结果</h2>
      <p>仅运行独立内置任务簿。实验观测与导入源码的静态推断分别保存。</p>
      <Feedback
        error={lab.error ?? history.error ?? detail.error ?? jobRun.error}
        retry={() => {
          void lab.refetch();
          void history.refetch();
          if (runId) void detail.refetch();
          else if (jobId) void jobRun.refetch();
        }}
      />
      {lab.isPending && <p role="status">读取实验说明…</p>}
      {lab.data && (
        <>
          <p>{lab.data.description}</p>
          <small>实验来源：{lab.data.example_version}</small>
          {lab.data.applicable ? (
            <PredictionForm
              key={`${selected.analysis}.${selected.endpoint}.${lab.data.version}`}
              lab={lab.data}
              selected={selected}
              onJob={(id) => {
                setPage(1);
                onJob(id);
              }}
            />
          ) : (
            <p role="status">{lab.data.applicability_reason}</p>
          )}
        </>
      )}
      {run && <RunResult run={run} onJob={onJob} onRun={onRun} />}
      <h3>实验历史</h3>
      {history.data?.count === 0 && <p>尚无实验运行记录。</p>}
      <ul>
        {history.data?.results.map((run) => (
          <li key={run.id}>
            <button type="button" onClick={() => onRun(run.id)}>
              {new Date(run.created_at).toLocaleString()} ·{' '}
              {states[run.job.status]}
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
      <SystemLabPanel
        selected={selected}
        runId={systemRunId}
        jobId={jobId}
        onRun={onSystemRun}
        onJob={onJob}
      />
    </section>
  );
}
function PredictionForm({
  lab,
  selected,
  onJob,
}: {
  lab: Lab;
  selected: LabSelection;
  onJob: (id: string) => void;
}) {
  const cache = useQueryClient();
  const [answers, setAnswers] = useState<
    Record<string, { status: string; writes: string }>
  >(() =>
    Object.fromEntries(cases.map((id) => [id, { status: '', writes: '' }])),
  );
  const operation = useIdempotentOperation<LabInputRequest, Job>(
    `lab.${selected.analysis}.${selected.endpoint}.${lab.version}`,
    (value) => JSON.stringify(value),
    submitRun,
    (job) => {
      void cache.invalidateQueries({ queryKey: ['labs', 'history'] });
      onJob(job.id);
    },
    onJob,
  );
  function update(id: string, key: 'status' | 'writes', value: string) {
    setAnswers((previous) => ({
      ...previous,
      [id]: { ...previous[id]!, [key]: value },
    }));
  }
  return (
    <form
      className="lab-predictions"
      onSubmit={(event) => {
        event.preventDefault();
        const prediction = (id: string) => ({
          status: Number(answers[id]!.status),
          writes: Number(answers[id]!.writes),
        });
        const predictions: PredictionsRequest = {
          normal: prediction('normal'),
          missing: prediction('missing'),
          empty: prediction('empty'),
          whitespace: prediction('whitespace'),
        };
        operation.start({
          snapshot_id: selected.snapshot,
          analysis_id: selected.analysis,
          endpoint_index: selected.endpoint,
          lab_version: lab.version,
          predictions,
        });
      }}
    >
      {lab.cases.map((item) => (
        <fieldset key={item.id}>
          <legend>{item.title}</legend>
          <code>{JSON.stringify(item.input)}</code>
          <label>
            预测 HTTP 状态
            <input
              type="number"
              min="100"
              max="599"
              step="1"
              required
              value={answers[item.id]!.status}
              onChange={(event) =>
                update(item.id, 'status', event.target.value)
              }
            />
          </label>
          <label>
            预测新增记录
            <select
              required
              value={answers[item.id]!.writes}
              onChange={(event) =>
                update(item.id, 'writes', event.target.value)
              }
            >
              <option value="">请选择</option>
              <option value="0">0 条</option>
              <option value="1">1 条</option>
            </select>
          </label>
        </fieldset>
      ))}
      <Button htmlType="submit" loading={operation.isPending}>
        {operation.pending ? '恢复这次实验提交' : '提交预测并运行实验'}
      </Button>
      <Feedback error={operation.error} />
    </form>
  );
}
function RunResult({
  run,
  onJob,
  onRun,
}: {
  run: LabRun;
  onJob: (id: string) => void;
  onRun: (id: string) => void;
}) {
  return (
    <section className="lab-result" aria-label="实验观测">
      <h3>{states[run.job.status]}</h3>
      <p>内置实验观测 · {run.definition.example_version}</p>
      <small>运行标识：{run.id}</small>
      <JobStatus
        id={run.job.id}
        snapshotId={null}
        onSelect={onJob}
        onResult={() => onRun(run.id)}
      />
      {run.observations.length === 0 && (
        <p>尚未取得可保存的请求响应；没有填充预设结果。</p>
      )}
      {run.observations.map((item) => {
        const caseId = cases.find((id) => id === item.case_id)!;
        const response = item.response;
        return (
          <article key={caseId}>
            <h4>
              {run.definition.cases.find((value) => value.id === caseId)?.title}
            </h4>
            <p>
              你的预测：HTTP {run.predictions[caseId].status}，新增{' '}
              {run.predictions[caseId].writes} 条
            </p>
            <p>
              实际响应：HTTP {response.status}；运行内记录{' '}
              {String(item.before_count)} →{' '}
              {item.after_count === null
                ? '未取得后续观测'
                : String(item.after_count)}
              ；请求耗时 {String(item.elapsed_ms)} ms
            </p>
            <details>
              <summary>实际请求与响应正文</summary>
              <p>POST {String(item.request_path)}</p>
              <pre>
                {JSON.stringify(
                  {
                    input: item.input,
                    response: response.body,
                    observed_at: item.observed_at,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </article>
        );
      })}
      <p role="status">
        清理状态：
        {run.cleanup.status === 'completed'
          ? '已确认仅清理本次运行数据'
          : run.cleanup.status === 'unconfirmed'
            ? '未确认；示例恢复后由过期核对进程清理，不能视为成功'
            : '尚无清理确认；运行异常中断时由示例过期核对进程处理'}
      </p>
    </section>
  );
}
