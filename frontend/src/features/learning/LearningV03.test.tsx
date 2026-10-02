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
import { LearningPathPanel } from './LearningPathPanel';
import { AttemptReviewPanel } from './AttemptReviewPanel';
import * as api from './api/paths-api';
import type {
  KnowledgeCurriculum,
  LearningPath,
} from '../../shared/api/generated/schema';
import { ApiError } from '../../shared/api/client';

vi.mock('./api/paths-api', async (original) => ({
  ...(await original<typeof api>()),
  listCurricula: vi.fn(),
  getCurriculum: vi.fn(),
  getPath: vi.fn(),
  listReviews: vi.fn(),
  submitReview: vi.fn(),
}));
const id = '00000000-0000-0000-0000-000000000001',
  selected = { snapshot: id, analysis: id, endpoint: 0 },
  empty = { count: 0, next: null, previous: null, results: [] };
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
    review_note: '合成教学安排',
    nodes: [
      { slug: 'a', card_version: '1' },
      { slug: 'b', card_version: '1' },
      { slug: 'z', card_version: '1' },
    ],
    edges: [{ prerequisite: 'a', dependent: 'b' }],
    goals: { 'create-task': ['b'], subprocess: ['z'] },
  },
};
const path: LearningPath = {
  snapshot_id: id,
  analysis_id: id,
  endpoint_index: 0,
  curriculum,
  goal: 'create-task',
  targets: ['b'],
  order: ['a', 'b'],
  steps: ['a', 'b'].map((slug) => ({
    id,
    slug,
    version: '1',
    title: `知识 ${slug}`,
    body: `内容 ${slug}`,
    applicability: '合成',
    review_note: '合成',
  })),
  applicable: true,
  applicability_reason: '源码版本匹配',
};
function mount(node: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {node}
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.listCurricula).mockResolvedValue({
    ...empty,
    count: 1,
    results: [curriculum],
  });
  vi.mocked(api.getCurriculum).mockResolvedValue(curriculum);
  vi.mocked(api.getPath).mockResolvedValue(path);
  vi.mocked(api.listReviews).mockResolvedValue(empty);
  vi.mocked(api.submitReview).mockImplementation(async (input) => ({
    id,
    ...input,
    note: input.note ?? '',
    created_at: '2026-10-01T00:00:00Z',
  }));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
test('路径绑定课程并按先修顺序展示，选择目标保留明确版本', async () => {
  const onSelect = vi.fn();
  mount(
    <LearningPathPanel
      selected={selected}
      curriculumId={id}
      goal="create-task"
      onSelect={onSelect}
    />,
  );
  await screen.findByText('知识 a');
  expect(
    screen
      .getAllByRole('listitem')
      .slice(0, 2)
      .map((item) => item.textContent),
  ).toEqual([
    expect.stringContaining('知识 a'),
    expect.stringContaining('知识 b'),
  ]);
  fireEvent.change(screen.getByLabelText('学习目标'), {
    target: { value: 'subprocess' },
  });
  expect(onSelect).toHaveBeenCalledWith(id, 'subprocess');
  expect(api.submitReview).not.toHaveBeenCalled();
});
test('DTO 拒绝环、缺失先修、卡片漂移和跨分析结果', () => {
  expect(api.parsePath(path, selected, id, 'create-task').order).toEqual([
    'a',
    'b',
  ]);
  expect(() =>
    api.parseCurriculum({
      ...curriculum,
      definition: {
        ...curriculum.definition,
        edges: [
          ...curriculum.definition.edges,
          { prerequisite: 'b', dependent: 'a' },
        ],
      },
    }),
  ).toThrow();
  expect(() =>
    api.parsePath(
      { ...path, order: ['b'], steps: [path.steps[1]] },
      selected,
      id,
      'create-task',
    ),
  ).toThrow();
  expect(() =>
    api.parsePath(
      { ...path, steps: [{ ...path.steps[0], version: '2' }, path.steps[1]] },
      selected,
      id,
      'create-task',
    ),
  ).toThrow();
  expect(() =>
    api.parsePath(path, { ...selected, endpoint: 1 }, id, 'create-task'),
  ).toThrow();
});
test('自评只有主动提交才追加，未知结果恢复原键且不存笔记正文', async () => {
  vi.mocked(api.submitReview).mockRejectedValueOnce(
    new ApiError('连接中断', 0),
  );
  mount(<AttemptReviewPanel attemptId={id} />);
  await screen.findByText('尚无自评记录。');
  expect(api.submitReview).not.toHaveBeenCalled();
  const choice = screen.getByLabelText('本次自评');
  choice.focus();
  expect(document.activeElement).toBe(choice);
  fireEvent.change(choice, { target: { value: 'understood' } });
  fireEvent.change(screen.getByLabelText('复习笔记'), {
    target: { value: '合成笔记' },
  });
  fireEvent.click(screen.getByRole('button', { name: '保存复习记录' }));
  await screen.findByText('连接中断');
  const first = vi.mocked(api.submitReview).mock.calls[0];
  expect(
    sessionStorage.getItem(`learning-lab.operation.review.${id}`),
  ).not.toContain('合成笔记');
  fireEvent.click(
    await screen.findByRole('button', { name: '用原输入恢复复习提交' }),
  );
  await waitFor(() => expect(api.submitReview).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.submitReview).mock.calls[1][1]).toBe(first[1]);
  await waitFor(() =>
    expect(
      sessionStorage.getItem(`learning-lab.operation.review.${id}`),
    ).toBeNull(),
  );
});
