import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
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
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function focusFrames() {
  let sequence = 0;
  const callbacks = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const id = ++sequence;
    callbacks.set(id, callback);
    return id;
  });
  vi.stubGlobal('cancelAnimationFrame', (id: number) => callbacks.delete(id));
  return {
    callbacks,
    advance() {
      const pending = [...callbacks.values()];
      callbacks.clear();
      act(() => {
        for (const callback of pending) callback(performance.now());
      });
    },
  };
}

test('知识目录切换只展示对应完整正文，不触发作答或自评写入', async () => {
  const second = {
    ...card,
    id: '00000000-0000-0000-0000-000000000002',
    title: '幂等恢复',
    body: '结果未知时保留同一个操作标识。',
  };
  vi.mocked(api.getCards).mockResolvedValue({
    ...empty,
    count: 2,
    results: [card, second],
  });
  panel();
  await screen.findByText(card.body);
  fireEvent.click(
    within(screen.getByRole('navigation', { name: '知识目录' })).getByRole(
      'button',
      { name: /幂等恢复/ },
    ),
  );
  expect(
    screen.getByRole('article', { name: '知识正文' }).textContent,
  ).toContain(second.body);
  expect(screen.queryByText(card.body)).toBeNull();
  fireEvent.click(
    within(screen.getByRole('navigation', { name: '知识目录' })).getByRole(
      'button',
      { name: /请求边界/ },
    ),
  );
  expect(screen.getByText(card.body)).toBeTruthy();
  expect(api.getCards).toHaveBeenCalledTimes(1);
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(paths.submitReview).not.toHaveBeenCalled();
});

test('初始读取不抢焦点，用户选卡等待正文测量后聚焦，同卡再选仍可定位', async () => {
  const frames = focusFrames();
  panel();
  const article = await screen.findByRole('article', { name: '知识正文' });
  const reading = screen.getByRole('region', { name: '知识正文区域' });
  expect(document.activeElement).not.toBe(reading);
  expect(frames.callbacks.size).toBe(0);
  const choice = within(
    screen.getByRole('navigation', { name: '知识目录' }),
  ).getByRole('button', { name: /请求边界/ });
  choice.focus();
  fireEvent.click(choice);
  frames.advance();
  expect(document.activeElement).toBe(choice);
  frames.advance();
  expect(document.activeElement).toBe(reading);
  expect(article.textContent).toContain(card.body);
  choice.focus();
  fireEvent.click(choice);
  frames.advance();
  frames.advance();
  expect(document.activeElement).toBe(reading);
  expect(api.getCards).toHaveBeenCalledTimes(1);
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(paths.submitReview).not.toHaveBeenCalled();
});

test('切换卡片只聚焦最后正文，换批次或隐藏模块不会迟到抢焦点', async () => {
  const frames = focusFrames();
  const second = {
    ...card,
    id: '00000000-0000-0000-0000-000000000002',
    title: '幂等恢复',
    body: '未知结果保留原标识。',
  };
  vi.mocked(api.getCards)
    .mockResolvedValueOnce({
      ...empty,
      count: 3,
      next: '/api/v1/knowledge-cards/?page=2',
      results: [card, second],
    })
    .mockResolvedValueOnce({ ...empty, count: 1, results: [card] });
  const view = panel();
  await screen.findByText(card.body);
  const directory = within(
    screen.getByRole('navigation', { name: '知识目录' }),
  );
  fireEvent.click(directory.getByRole('button', { name: /请求边界/ }));
  fireEvent.click(directory.getByRole('button', { name: /幂等恢复/ }));
  frames.advance();
  frames.advance();
  expect(document.activeElement).toBe(
    screen.getByRole('region', { name: '知识正文区域' }),
  );
  expect(
    screen.getByRole('article', { name: '知识正文' }).textContent,
  ).toContain(second.body);
  fireEvent.click(directory.getByRole('button', { name: /幂等恢复/ }));
  frames.advance();
  const next = screen.getByRole('button', { name: '下一批记录' });
  next.focus();
  fireEvent.click(next);
  await screen.findByText(card.body);
  frames.advance();
  frames.advance();
  expect(document.activeElement).not.toBe(
    screen.getByRole('region', { name: '知识正文区域' }),
  );
  expect(frames.callbacks.size).toBe(0);
  const currentChoice = within(
    screen.getByRole('navigation', { name: '知识目录' }),
  ).getByRole('button', { name: /请求边界/ });
  currentChoice.focus();
  fireEvent.click(currentChoice);
  const region = screen.getByRole('region', { name: '知识与学习' });
  region.setAttribute('hidden', '');
  frames.advance();
  frames.advance();
  expect(document.activeElement).toBe(currentChoice);
  expect(api.submitAttempt).not.toHaveBeenCalled();
  expect(paths.submitReview).not.toHaveBeenCalled();
  region.removeAttribute('hidden');
  fireEvent.click(currentChoice);
  expect(frames.callbacks.size).toBe(1);
  view.unmount();
  expect(frames.callbacks.size).toBe(0);
});

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
  fireEvent.click(screen.getByRole('button', { name: '下一批记录' }));
  await screen.findByText('暂无已发布知识卡片。');
  await waitFor(() =>
    expect(api.getCards).toHaveBeenLastCalledWith(2, expect.any(AbortSignal)),
  );
  cleanup();
  vi.mocked(api.getCards).mockRejectedValue(new Error('知识卡片读取失败'));
  panel();
  await screen.findByText('知识卡片读取失败');
});
