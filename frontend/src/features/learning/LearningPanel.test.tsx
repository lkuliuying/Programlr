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
import { LearningPanel } from './LearningPanel';
import * as api from './api/learning-api';
import * as paths from './api/paths-api';
import type {
  Exercise,
  ExerciseAttempt,
} from '../../shared/api/generated/schema';

vi.mock('./api/learning-api', async (original) => ({
  ...(await original<typeof api>()),
  getCards: vi.fn(),
  getExercises: vi.fn(),
  attemptHistory: vi.fn(),
  getAttempt: vi.fn(),
  submitAttempt: vi.fn(),
}));
vi.mock('./api/paths-api', async (original) => ({
  ...(await original<typeof paths>()),
  listCurricula: vi.fn(),
  listReviews: vi.fn(),
}));
const id = '00000000-0000-0000-0000-000000000001',
  selected = { snapshot: id, analysis: id, endpoint: 0 };
const exercise: Exercise = {
  id,
  slug: 'order',
  version: '1',
  answer_version: '1',
  example_version: 'task-board/1.0.0',
  kind: 'flow_order',
  question: '排列流程',
  hint: '请求先于写入',
  options: [
    { id: 'write', label: '写入数据库' },
    { id: 'request', label: '发出请求' },
  ],
  review_note: '人工维护的固定题',
  applicable: true,
  applicability_reason: '匹配',
};
const empty = { count: 0, next: null, previous: null, results: [] };
const attempt: ExerciseAttempt = {
  previous_attempt_id: null,
  id,
  exercise_id: id,
  exercise_version: '1',
  answer_version: '1',
  example_version: 'task-board/1.0.0',
  snapshot_id: id,
  analysis_id: id,
  endpoint_index: 0,
  question: '排列流程',
  kind: 'flow_order',
  answer: ['request', 'write'],
  hint_used: true,
  correct: true,
  created_at: '2026-09-29T00:00:00Z',
  feedback: {
    expected_answer: ['request', 'write'],
    explanation: '固定反馈内容',
    source_refs: [],
  },
};
const onAttempt = vi.fn();
function panel(attemptId: string | null = null) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LearningPanel
        selected={selected}
        attemptId={attemptId}
        onAttempt={onAttempt}
        onSource={vi.fn()}
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.getCards).mockResolvedValue(empty);
  vi.mocked(paths.listCurricula).mockResolvedValue(empty);
  vi.mocked(paths.listReviews).mockResolvedValue(empty);
  vi.mocked(api.attemptHistory).mockResolvedValue(empty);
  vi.mocked(api.getExercises).mockResolvedValue({
    ...empty,
    count: 1,
    results: [exercise],
  });
  vi.mocked(api.submitAttempt).mockResolvedValue(attempt);
  vi.mocked(api.getAttempt).mockResolvedValue(attempt);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('排序使用可聚焦按钮，提交前不展示标准答案并记录提示', async () => {
  panel();
  await screen.findByText('排列流程');
  expect(screen.queryByText('本次答案与标准答案')).toBeNull();
  const up = screen.getByRole('button', { name: '上移第 2 步' });
  up.focus();
  expect(document.activeElement).toBe(up);
  fireEvent.click(up);
  fireEvent.click(screen.getByText('查看提示'));
  fireEvent.click(screen.getByText('提交作答'));
  await waitFor(() => expect(api.submitAttempt).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.submitAttempt).mock.calls[0][1]).toMatchObject({
    answer: ['request', 'write'],
    hint_used: true,
    exercise_version: '1',
  });
  await waitFor(() => expect(onAttempt).toHaveBeenCalledWith(id));
});
test('重新挂载按 URL 标识读取历史反馈及答案版本', async () => {
  panel(id);
  await screen.findByText('固定反馈内容');
  expect(screen.getByText(/答案版本 1/)).toBeTruthy();
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(api.getAttempt).toHaveBeenCalledWith(
    selected,
    id,
    expect.any(AbortSignal),
  );
});
test('版本不匹配的工作区没有作答表单', async () => {
  vi.mocked(api.getExercises).mockResolvedValue({
    ...empty,
    count: 1,
    results: [{ ...exercise, applicable: false }],
  });
  panel();
  await screen.findByText(/无对应练习/);
  expect(screen.queryByText('提交作答')).toBeNull();
});
test('运行时校验拒绝非法类型答案及其他接口历史', () => {
  expect(() =>
    api.typedAnswer({ x: { status: true, writes: 1 } }, 'error_prediction'),
  ).toThrow();
  expect(() =>
    api.typedAnswer(
      { file_path: '../x', start_line: 1, end_line: 2 },
      'code_location',
    ),
  ).toThrow();
  expect(() =>
    api.parseAttempt(attempt, { ...selected, endpoint: 1 }),
  ).toThrow();
});

test('重新练习重置提示并把新作答关联原记录', async () => {
  panel(id);
  await screen.findByText('本次作答正确');
  fireEvent.click(screen.getByRole('button', { name: '重新练习这道题' }));
  await screen.findByText('本次重新练习关联原作答，提交后新增记录。');
  fireEvent.click(screen.getByRole('button', { name: '提交作答' }));
  await waitFor(() => expect(api.submitAttempt).toHaveBeenCalled());
  expect(vi.mocked(api.submitAttempt).mock.calls[0][1]).toMatchObject({
    previous_attempt_id: id,
    hint_used: false,
  });
});

test('练习独立读取题目和作答，不加载知识卡片或课程路径', async () => {
  panel();
  await screen.findByText('排列流程');
  expect(screen.queryByRole('region', { name: '知识卡片' })).toBeNull();
  expect(screen.queryByRole('region', { name: '知识先修路径' })).toBeNull();
  expect(screen.queryByLabelText('课程版本')).toBeNull();
  expect(api.getCards).not.toHaveBeenCalled();
  expect(paths.listCurricula).not.toHaveBeenCalled();
  expect(api.getExercises).toHaveBeenCalledWith(
    selected,
    1,
    expect.any(AbortSignal),
  );
  expect(api.submitAttempt).not.toHaveBeenCalled();
});
