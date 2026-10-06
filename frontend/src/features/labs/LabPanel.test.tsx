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
import { LabPanel } from './LabPanel';
import * as api from './api/labs-api';
import * as systemApi from './api/system-labs-api';
import type { Job, Lab, LabRun } from '../../shared/api/generated/schema';
import { ApiError } from '../../shared/api/client';

vi.mock('./api/labs-api', async (original) => ({
  ...(await original<typeof api>()),
  getLab: vi.fn(),
  listRuns: vi.fn(),
  getRun: vi.fn(),
  getRunForJob: vi.fn(),
  submitRun: vi.fn(),
}));
vi.mock('./api/system-labs-api', async (original) => ({
  ...(await original<typeof systemApi>()),
  listSystemLabs: vi.fn(),
  listSystemRuns: vi.fn(),
  getSystemRunForJob: vi.fn(),
}));
vi.mock('../jobs', async (original) => ({
  ...(await original<object>()),
  JobStatus: () => <div>任务状态</div>,
}));
const id = '00000000-0000-0000-0000-000000000001',
  selected = { snapshot: id, analysis: id, endpoint: 0 };
const lab: Lab = {
  id: 'request-validation',
  version: '1',
  title: '请求校验',
  example_version: 'task-board/1.0.0+request-validation/1',
  description: '独立示例',
  applicable: true,
  applicability_reason: '匹配',
  cases: api.cases.map((id) => ({ id, title: id, input: {} })),
};
const job: Job = {
  id,
  kind: 'lab',
  status: 'queued',
  stage: 'queued',
  progress: null,
  snapshot_id: null,
  previous_job_id: null,
  parent_job_id: null,
  source_kind: '',
  result_deleted_at: null,
  result_deleted: false,
  result_url: null,
  error: null,
  created_at: '2026-09-29T00:00:00Z',
  updated_at: '2026-09-29T00:00:00Z',
};
const empty = { count: 0, next: null, previous: null, results: [] };
const onJob = vi.fn();
function panel(runId: string | null = null, jobId: string | null = null) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <LabPanel
        selected={selected}
        runId={runId}
        jobId={jobId}
        onRun={vi.fn()}
        onJob={onJob}
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.getLab).mockResolvedValue(lab);
  vi.mocked(systemApi.listSystemLabs).mockResolvedValue(empty);
  vi.mocked(systemApi.listSystemRuns).mockResolvedValue(empty);
  vi.mocked(systemApi.getSystemRunForJob).mockResolvedValue(null);
  vi.mocked(api.listRuns).mockResolvedValue(empty);
  vi.mocked(api.submitRun).mockResolvedValue(job);
  vi.mocked(api.getRunForJob).mockResolvedValue(null);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('必须先填写预测，显式提交一次并保持四类输入', async () => {
  panel();
  await screen.findByText('独立示例');
  const inputs = screen.getAllByRole('spinbutton');
  expect(
    inputs.every(
      (input) =>
        (input as HTMLInputElement).required &&
        (input as HTMLInputElement).value === '',
    ),
  ).toBe(true);
  inputs.forEach((input) =>
    fireEvent.change(input, { target: { value: '400' } }),
  );
  screen
    .getAllByRole('combobox')
    .forEach((input) => fireEvent.change(input, { target: { value: '0' } }));
  fireEvent.click(screen.getByRole('button', { name: '提交预测并运行实验' }));
  await waitFor(() => expect(onJob).toHaveBeenCalledWith(id));
  expect(api.submitRun).toHaveBeenCalledTimes(1);
  expect(vi.mocked(api.submitRun).mock.calls[0][0].predictions.normal).toEqual({
    status: 400,
    writes: 0,
  });
});
test('不匹配时没有运行入口，读取错误可以恢复', async () => {
  vi.mocked(api.getLab).mockResolvedValue({
    ...lab,
    applicable: false,
    applicability_reason: '没有对应实验',
  });
  panel();
  await screen.findByText('没有对应实验');
  expect(
    screen.queryByRole('button', { name: '提交预测并运行实验' }),
  ).toBeNull();
  expect(api.submitRun).not.toHaveBeenCalled();
});
test('失败历史显示缺失观测与未知清理，不显示模拟成功', async () => {
  const run: LabRun = {
    id,
    job: { ...job, status: 'failed' },
    snapshot_id: id,
    analysis_id: id,
    endpoint_index: 0,
    definition: lab,
    predictions: {
      normal: { status: 201, writes: 1 },
      missing: { status: 400, writes: 0 },
      empty: { status: 400, writes: 0 },
      whitespace: { status: 400, writes: 0 },
    },
    observations: [],
    cleanup: {
      status: 'unconfirmed',
      observation: null,
      error_code: 'LAB_UNAVAILABLE',
    },
    created_at: job.created_at,
  };
  vi.mocked(api.getRun).mockResolvedValue(run);
  panel(id);
  await screen.findByText('实验失败');
  expect(screen.getByText(/尚未取得可保存的请求响应/)).toBeTruthy();
  expect(screen.getByText(/不能视为成功/)).toBeTruthy();
});
test('运行时校验拒绝跨快照结果', () => {
  expect(() =>
    api.parseRun(
      { id, job, snapshot_id: 'wrong', analysis_id: id, endpoint_index: 0 },
      selected,
    ),
  ).toThrow();
});

test('新重试运行不在历史页时仍按任务标识显示', async () => {
  vi.mocked(api.getRunForJob).mockResolvedValue({
    id,
    job: { ...job, status: 'running' },
    snapshot_id: id,
    analysis_id: id,
    endpoint_index: 0,
    definition: lab,
    predictions: {
      normal: { status: 201, writes: 1 },
      missing: { status: 400, writes: 0 },
      empty: { status: 400, writes: 0 },
      whitespace: { status: 400, writes: 0 },
    },
    observations: [],
    cleanup: { status: 'pending', observation: null, error_code: null },
    created_at: job.created_at,
  });
  panel(null, id);
  await screen.findByRole('heading', { name: '执行中' });
  expect(api.getRunForJob).toHaveBeenCalledWith(
    selected,
    id,
    expect.any(AbortSignal),
  );
  expect(screen.getByText('尚无实验运行记录。')).toBeTruthy();
});

test('确定的实验版本冲突释放操作键，允许修正预测后重新提交', async () => {
  vi.mocked(api.submitRun).mockRejectedValueOnce(
    new ApiError('实验版本已变化', 409, 'trace', 'LAB_VERSION_MISMATCH'),
  );
  panel();
  await screen.findByText('独立示例');
  screen
    .getAllByRole('spinbutton')
    .forEach((input) => fireEvent.change(input, { target: { value: '400' } }));
  screen
    .getAllByRole('combobox')
    .forEach((input) => fireEvent.change(input, { target: { value: '0' } }));
  fireEvent.click(screen.getByRole('button', { name: '提交预测并运行实验' }));
  await screen.findByText(/实验版本已变化/);
  expect(sessionStorage.length).toBe(0);
  fireEvent.change(screen.getAllByRole('spinbutton')[0], {
    target: { value: '201' },
  });
  fireEvent.click(
    await screen.findByRole('button', { name: /提交预测并运行实验/ }),
  );
  await waitFor(() => expect(onJob).toHaveBeenCalledWith(id));
  expect(api.submitRun).toHaveBeenCalledTimes(2);
  expect(vi.mocked(api.submitRun).mock.calls[0][1]).not.toBe(
    vi.mocked(api.submitRun).mock.calls[1][1],
  );
});
