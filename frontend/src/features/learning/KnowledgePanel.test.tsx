import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type {
  KnowledgeCard,
  KnowledgeCurriculum,
  LearningPath,
} from '../../shared/api/generated/schema';
import { KnowledgePanel } from './KnowledgePanel';
import * as api from './api/learning-api';
import * as paths from './api/paths-api';

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
  getCurriculum: vi.fn(),
  getPath: vi.fn(),
  listReviews: vi.fn(),
  submitReview: vi.fn(),
}));

const id = '00000000-0000-0000-0000-000000000001';
const selected = { snapshot: id, analysis: id, endpoint: 0 };
const empty = { count: 0, next: null, previous: null, results: [] };
const card: KnowledgeCard = {
  id,
  slug: 'request',
  version: '1',
  title: '请求边界',
  body: '验证输入后再提交写入。',
  applicability: '通用知识，结合当前源码核对。',
  review_note: '合成教学卡片。',
};
const curriculum: KnowledgeCurriculum = {
  id,
  slug: 'course',
  version: '1',
  title: '合成知识课程',
  content_digest: 'a'.repeat(64),
  definition: {
    slug: 'course',
    version: '1',
    title: '合成知识课程',
    example_version: 'task-board/1.0.0',
    review_note: '合成教学安排。',
    nodes: [{ slug: 'request', card_version: '1' }],
    edges: [],
    goals: { 'create-task': ['request'] },
  },
};
const path: LearningPath = {
  snapshot_id: id,
  analysis_id: id,
  endpoint_index: 0,
  curriculum,
  goal: 'create-task',
  targets: ['request'],
  order: ['request'],
  steps: [card],
  applicable: true,
  applicability_reason: '源码版本匹配',
};
function panel(selection: api.LearningSelection | null = null) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <KnowledgePanel
        selected={selection}
        curriculumId={selection ? id : null}
        goal="create-task"
        onPath={vi.fn()}
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getCards).mockResolvedValue({
    ...empty,
    count: 1,
    results: [card],
  });
  vi.mocked(paths.listCurricula).mockResolvedValue({
    ...empty,
    count: 1,
    results: [curriculum],
  });
  vi.mocked(paths.getCurriculum).mockResolvedValue(curriculum);
  vi.mocked(paths.getPath).mockResolvedValue(path);
});
afterEach(cleanup);

test('未选择接口仍可阅读全局卡片，学习路径提供独立引导', async () => {
  panel();
  await screen.findByText('请求边界 · v1');
  expect(screen.getByText(/先在 API 分析选择接口/)).toBeTruthy();
  expect(paths.listCurricula).not.toHaveBeenCalled();
  expect(paths.getPath).not.toHaveBeenCalled();
  expect(screen.queryByRole('region', { name: '固定练习' })).toBeNull();
  expect(screen.queryByRole('button', { name: '提交作答' })).toBeNull();
  expect(api.getExercises).not.toHaveBeenCalled();
  expect(api.attemptHistory).not.toHaveBeenCalled();
  expect(api.getAttempt).not.toHaveBeenCalled();
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(paths.submitReview).not.toHaveBeenCalled();
});

test('有接口时读取对应课程路径，知识页不包含作答和实验操作', async () => {
  panel(selected);
  await screen.findByText('源码版本匹配');
  expect(paths.getPath).toHaveBeenCalledWith(
    selected,
    id,
    'create-task',
    expect.any(AbortSignal),
  );
  expect(screen.getByLabelText('课程版本')).toBeTruthy();
  expect(screen.getByLabelText('学习目标')).toBeTruthy();
  expect(screen.queryByRole('region', { name: '复习与自我判断' })).toBeNull();
  expect(screen.queryByRole('region', { name: '内置实验' })).toBeNull();
  expect(screen.queryByRole('button', { name: '查看提示' })).toBeNull();
  expect(api.getExercises).not.toHaveBeenCalled();
  expect(paths.listReviews).not.toHaveBeenCalled();
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(paths.submitReview).not.toHaveBeenCalled();
});

test('知识卡片分页读取所选页，空内容和读取失败明确呈现', async () => {
  vi.mocked(api.getCards)
    .mockResolvedValueOnce({
      ...empty,
      count: 2,
      next: '/api/v1/knowledge-cards/?page=2',
      results: [card],
    })
    .mockResolvedValueOnce(empty);
  panel();
  await screen.findByText('请求边界 · v1');
  fireEvent.click(screen.getByRole('button', { name: '下一页' }));
  await screen.findByText('暂无已发布知识卡片。');
  await waitFor(() =>
    expect(api.getCards).toHaveBeenLastCalledWith(2, expect.any(AbortSignal)),
  );
  cleanup();
  vi.mocked(api.getCards).mockRejectedValue(new Error('知识卡片读取失败'));
  panel();
  await screen.findByText('知识卡片读取失败');
});
