import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SystemLabPanel } from './SystemLabPanel';
import * as api from './api/system-labs-api';
import type {
  Job,
  SystemLab,
  SystemLabRun,
} from '../../shared/api/generated/schema';

vi.mock('./api/system-labs-api', async (original) => ({
  ...(await original<typeof api>()),
  listSystemLabs: vi.fn(),
  listSystemRuns: vi.fn(),
  getSystemRun: vi.fn(),
  getSystemRunForJob: vi.fn(),
  submitSystemRun: vi.fn(),
}));
vi.mock('../jobs', async (original) => ({
  ...(await original<object>()),
  JobStatus: () => <div>持久化任务</div>,
}));
const id = '00000000-0000-0000-0000-000000000001',
  selected = { snapshot: id, analysis: id, endpoint: 0 },
  empty = { count: 0, next: null, previous: null, results: [] };
const lab: SystemLab = {
  id: 'subprocess-lifecycle',
  version: '1',
  title: '合成进程实验',
  example_version: 'system-labs/1.0.0',
  program_digest: 'a'.repeat(64),
  description: '固定可信程序',
  applicable: true,
  applicability_reason: '匹配',
  cases: [
    { id: 'first', title: '正常', prediction_label: '正常模式能否退出' },
    { id: 'second', title: '超时', prediction_label: '超时模式能否退出' },
  ],
};
const job: Job = {
  id,
  kind: 'lab',
  status: 'succeeded',
  stage: 'done',
  progress: null,
  snapshot_id: null,
  previous_job_id: null,
  parent_job_id: null,
  source_kind: '',
  result_deleted_at: null,
  result_deleted: false,
  result_url: `/api/v1/system-lab-runs/${id}/`,
  error: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
};
const run: SystemLabRun = {
  id,
  job,
  snapshot_id: id,
  analysis_id: id,
  endpoint_index: 0,
  lab_id: lab.id,
  definition: lab,
  predictions: { first: true, second: false },
  observations: ['first', 'second'].map((case_id, index) => ({
    case_id: index === 0 ? 'first' : 'second',
    status: 'observed',
    hostname: null,
    addresses: [],
    connected: null,
    pid: 101 + index,
    return_code: index === 0 ? 0 : -9,
    stdout: index === 0 ? 'ready\ncompleted\n' : 'ready\n',
    timed_out: index === 1,
    reaped: true,
    error_code: null,
    elapsed_ms: index === 0 ? 23 : 501,
    observed_at: '2026-10-01T00:00:00Z',
  })),
  cleanup: { status: 'completed', error_code: null },
  created_at: '2026-10-01T00:00:00Z',
};
function panel(runId: string | null = null) {
  const onJob = vi.fn();
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <SystemLabPanel
        selected={selected}
        runId={runId}
        jobId={null}
        onRun={vi.fn()}
        onJob={onJob}
      />
    </QueryClientProvider>,
  );
  return onJob;
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.listSystemLabs).mockResolvedValue({
    ...empty,
    count: 1,
    results: [lab],
  });
  vi.mocked(api.listSystemRuns).mockResolvedValue(empty);
  vi.mocked(api.getSystemRun).mockResolvedValue(run);
  vi.mocked(api.submitSystemRun).mockResolvedValue(job);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('先提交两个预测，不开放命令输入且主动启动一次', async () => {
  const onJob = panel();
  await screen.findByText('固定可信程序');
  expect(api.submitSystemRun).not.toHaveBeenCalled();
  const choice = screen.getByLabelText('正常模式能否退出');
  choice.focus();
  expect(document.activeElement).toBe(choice);
  fireEvent.change(choice, { target: { value: 'yes' } });
  fireEvent.change(screen.getByLabelText('超时模式能否退出'), {
    target: { value: 'no' },
  });
  fireEvent.click(
    screen.getByRole('button', { name: '提交预测并运行合成进程实验' }),
  );
  await waitFor(() => expect(onJob).toHaveBeenCalledWith(id));
  expect(api.submitSystemRun).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.submitSystemRun).mock.calls[0][0]).toMatchObject({
    lab_id: lab.id,
    predictions: { first: true, second: false },
  });
});
test('读取历史显示真实 PID 和回收，不隐式重跑', async () => {
  panel(id);
  await screen.findByText('合成进程实验 · 真实观测已保存');
  expect(screen.getByText(/PID：101/)).toBeTruthy();
  expect(screen.getByText(/PID：102/)).toBeTruthy();
  expect(screen.getAllByText(/已 wait 回收/)).toHaveLength(2);
  expect(api.submitSystemRun).not.toHaveBeenCalled();
});
test('校验拒绝跨工作区、错误结果链接、伪回收和重复用例', () => {
  expect(api.parseSystemRun(run, selected).observations).toHaveLength(2);
  expect(() => api.parseSystemRun(run, { ...selected, endpoint: 1 })).toThrow();
  expect(() =>
    api.parseSystemRun(
      { ...run, job: { ...job, result_url: `/api/v1/lab-runs/${id}/` } },
      selected,
    ),
  ).toThrow();
  expect(() =>
    api.parseSystemRun(
      {
        ...run,
        observations: [
          { ...run.observations[0], reaped: false },
          run.observations[1],
        ],
      },
      selected,
    ),
  ).toThrow();
  expect(() =>
    api.parseSystemRun(
      { ...run, observations: [run.observations[0], run.observations[0]] },
      selected,
    ),
  ).toThrow();
});
