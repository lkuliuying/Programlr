import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type {
  CurriculumProgress,
  KnowledgeCard,
  KnowledgeCurriculum,
} from '../../shared/api/generated/schema';
import { ApiError } from '../../shared/api/client';
import { CourseReader } from './CourseReader';
import { CourseSummary } from './CourseSummary';
import * as paths from './api/paths-api';
import * as api from './api/course-api';

vi.mock('./api/paths-api', async (original) => ({
  ...(await original<typeof paths>()),
  listCurricula: vi.fn(),
  getCurriculum: vi.fn(),
}));
vi.mock('./api/course-api', async (original) => ({
  ...(await original<typeof api>()),
  getCourseProgress: vi.fn(),
  getCourseCard: vi.fn(),
  setCourseCardProgress: vi.fn(),
}));

const id = '00000000-0000-0000-0000-000000000001';
const cardId = '00000000-0000-0000-0000-000000000011';
const secondId = '00000000-0000-0000-0000-000000000012';
const course: KnowledgeCurriculum = {
  id,
  slug: 'course',
  version: '1',
  title: '请求与恢复',
  content_digest: 'a'.repeat(64),
  definition: {
    slug: 'course',
    version: '1',
    title: '请求与恢复',
    example_version: 'task-board/1.0.0',
    review_note: '固定教学安排',
    nodes: [
      { slug: 'request', card_version: '1' },
      { slug: 'recovery', card_version: '1' },
    ],
    edges: [{ prerequisite: 'request', dependent: 'recovery' }],
    goals: { basics: ['recovery'] },
  },
};
const card: KnowledgeCard = {
  id: cardId,
  slug: 'request',
  version: '1',
  title: '请求边界',
  body: '先核对输入，再提交受控写入。',
  applicability: '通用知识',
  review_note: '固定正文',
};
const secondCard: KnowledgeCard = {
  ...card,
  id: secondId,
  slug: 'recovery',
  title: '恢复核实',
  body: '未知结果先读取，再决定下一步。',
};
const empty = { count: 0, next: null, previous: null, results: [] };
function state(completed = false, selectedCourse = course): CurriculumProgress {
  return {
    curriculum_id: selectedCourse.id,
    version: selectedCourse.version,
    completed_count: completed ? 1 : 0,
    total_count: 2,
    cards: [
      {
        card_id: cardId,
        slug: 'request',
        version: '1',
        title: card.title,
        completed,
      },
      {
        card_id: secondId,
        slug: 'recovery',
        version: '1',
        title: secondCard.title,
        completed: false,
      },
    ],
  };
}
function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}
function reader(courseId: string | null = id, active = true, cache = client()) {
  const select = vi.fn();
  const view = render(
    <QueryClientProvider client={cache}>
      <CourseReader
        courseId={courseId}
        active={active}
        onSelectCourse={select}
      />
    </QueryClientProvider>,
  );
  return { ...view, select, cache };
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(paths.listCurricula).mockResolvedValue({
    ...empty,
    count: 1,
    results: [course],
  });
  vi.mocked(paths.getCurriculum).mockResolvedValue(course);
  vi.mocked(api.getCourseProgress).mockResolvedValue(state());
  vi.mocked(api.getCourseCard).mockImplementation(async (item) =>
    item.card_id === cardId ? card : secondCard,
  );
  vi.mocked(api.setCourseCardProgress).mockResolvedValue(state(true));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('无项目或接口也能显式选课，初始读取与翻目录不提交阅读状态', async () => {
  const view = reader(null);
  await screen.findByRole('button', { name: '请求与恢复 · 1' });
  expect(paths.getCurriculum).not.toHaveBeenCalled();
  expect(api.getCourseProgress).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '请求与恢复 · 1' }));
  expect(view.select).toHaveBeenCalledWith(id);
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
  expect(screen.getByText('选择一门课程开始阅读。')).toBeTruthy();
});

test('新课程显示真实零进度，用户显式标记和撤销才写入并同步首页', async () => {
  let saved = state();
  vi.mocked(api.getCourseProgress).mockImplementation(async () => saved);
  vi.mocked(api.setCourseCardProgress).mockImplementation(
    async (_course, _card, completed) => {
      saved = state(completed);
      return saved;
    },
  );
  const cache = client();
  const select = vi.fn();
  render(
    <QueryClientProvider client={cache}>
      <CourseSummary onSelectCourse={select} />
      <CourseReader courseId={id} onSelectCourse={select} />
    </QueryClientProvider>,
  );
  await screen.findByRole('button', { name: '标记已阅读' });
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
  expect(screen.getAllByText('已阅读 0 / 2')).toHaveLength(2);
  const mark = screen.getByRole('button', { name: '标记已阅读' });
  await waitFor(() => expect(mark).toHaveProperty('disabled', false));
  fireEvent.click(mark);
  fireEvent.click(mark);
  await waitFor(() =>
    expect(screen.getAllByText('已阅读 1 / 2')).toHaveLength(2),
  );
  expect(api.setCourseCardProgress).toHaveBeenCalledTimes(1);
  expect(api.setCourseCardProgress).toHaveBeenLastCalledWith(
    course,
    state().cards[0],
    true,
    expect.any(AbortSignal),
  );
  const undo = screen.getByRole('button', { name: '撤销已阅读' });
  await waitFor(() => expect(undo).toHaveProperty('disabled', false));
  fireEvent.click(undo);
  await waitFor(() =>
    expect(screen.getAllByText('已阅读 0 / 2')).toHaveLength(2),
  );
  expect(api.setCourseCardProgress).toHaveBeenCalledTimes(2);
  expect(api.setCourseCardProgress).toHaveBeenLastCalledWith(
    course,
    expect.objectContaining({ card_id: cardId }),
    false,
    expect.any(AbortSignal),
  );
  expect(screen.getByText(/不评价掌握程度/)).toBeTruthy();
});

test('目录阅读保持完整正文，异步选卡后才聚焦，同卡再选仍可定位且不写', async () => {
  let nextFrame = 0;
  const frames = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const frame = ++nextFrame;
    frames.set(frame, callback);
    return frame;
  });
  vi.stubGlobal('cancelAnimationFrame', (frame: number) =>
    frames.delete(frame),
  );
  const advance = () =>
    act(() => {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback(performance.now()));
    });
  reader();
  await screen.findByText(card.body);
  expect(frames.size).toBe(0);
  const directory = within(
    screen.getByRole('navigation', { name: '课程卡片目录' }),
  );
  const choice = directory.getByRole('button', { name: /恢复核实/ });
  choice.focus();
  fireEvent.click(choice);
  await screen.findByText(secondCard.body);
  advance();
  expect(document.activeElement).toBe(choice);
  advance();
  const body = screen.getByRole('region', { name: '课程卡片正文区域' });
  expect(document.activeElement).toBe(body);
  choice.focus();
  fireEvent.click(choice);
  advance();
  advance();
  expect(document.activeElement).toBe(body);
  expect(
    screen.getByRole('article', { name: '课程卡片正文' }).textContent,
  ).toContain(secondCard.body);
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
});

test('写入未知时只发一次，先 GET 核实才恢复按钮，不自动重复 PATCH', async () => {
  vi.mocked(api.setCourseCardProgress).mockRejectedValue(
    new ApiError('连接未完成', 0),
  );
  const view = reader();
  const mark = await screen.findByRole('button', { name: '标记已阅读' });
  fireEvent.click(mark);
  const verify = await screen.findByRole('button', { name: '核实已阅读状态' });
  expect(screen.getByRole('button', { name: '标记已阅读' })).toHaveProperty(
    'disabled',
    true,
  );
  vi.mocked(api.getCourseProgress).mockResolvedValue(state(true));
  fireEvent.click(verify);
  await screen.findByRole('button', { name: '撤销已阅读' });
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: '核实已阅读状态' })).toBeNull(),
  );
  expect(api.setCourseCardProgress).toHaveBeenCalledTimes(1);
  expect(api.getCourseProgress).toHaveBeenCalledTimes(2);
  expect(view.cache.getQueryData(api.courseProgressKey(id, '1'))).toEqual(
    state(true),
  );
});

test('显式同课再选定位课程内容，隐藏后取消迟到焦点并在卸载释放帧', async () => {
  let nextFrame = 0;
  const frames = new Map<number, FrameRequestCallback>();
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
    const frame = ++nextFrame;
    frames.set(frame, callback);
    return frame;
  });
  vi.stubGlobal('cancelAnimationFrame', (frame: number) =>
    frames.delete(frame),
  );
  const advance = () =>
    act(() => {
      const pending = [...frames.values()];
      frames.clear();
      pending.forEach((callback) => callback(performance.now()));
    });
  const view = reader();
  await screen.findByText(card.body);
  expect(frames.size).toBe(0);
  const choice = screen.getByRole('button', { name: '请求与恢复 · 1' });
  choice.focus();
  fireEvent.click(choice);
  advance();
  advance();
  expect(document.activeElement).toBe(
    screen.getByRole('region', { name: '所选课程阅读' }),
  );
  choice.focus();
  fireEvent.click(choice);
  expect(frames.size).toBe(1);
  view.rerender(
    <QueryClientProvider client={view.cache}>
      <CourseReader courseId={id} active={false} onSelectCourse={view.select} />
    </QueryClientProvider>,
  );
  advance();
  advance();
  expect(document.activeElement).toBe(choice);
  expect(frames.size).toBe(0);
  view.rerender(
    <QueryClientProvider client={view.cache}>
      <CourseReader courseId={id} onSelectCourse={view.select} />
    </QueryClientProvider>,
  );
  fireEvent.click(choice);
  expect(frames.size).toBe(1);
  view.unmount();
  expect(frames.size).toBe(0);
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
});

test('核实读取失败继续阻止写入，明确拒绝仍显示服务端错误', async () => {
  vi.mocked(api.setCourseCardProgress).mockRejectedValue(
    new ApiError('连接未完成', 0),
  );
  reader();
  fireEvent.click(await screen.findByRole('button', { name: '标记已阅读' }));
  await screen.findByRole('button', { name: '核实已阅读状态' });
  vi.mocked(api.getCourseProgress).mockRejectedValue(
    new ApiError('核实读取失败', 503),
  );
  fireEvent.click(screen.getByRole('button', { name: '核实已阅读状态' }));
  await screen.findByText('核实读取失败');
  expect(screen.getByRole('button', { name: '标记已阅读' })).toHaveProperty(
    'disabled',
    true,
  );
  expect(api.setCourseCardProgress).toHaveBeenCalledTimes(1);
  cleanup();
  vi.mocked(api.getCourseProgress).mockResolvedValue(state());
  vi.mocked(api.setCourseCardProgress).mockRejectedValue(
    new ApiError('卡片版本不属于课程', 400),
  );
  reader();
  fireEvent.click(await screen.findByRole('button', { name: '标记已阅读' }));
  await screen.findByText('卡片版本不属于课程');
  expect(screen.queryByRole('button', { name: '核实已阅读状态' })).toBeNull();
});

test('切换课程版本取消旧写入，迟到成功不污染新课程或首页缓存', async () => {
  const newer = {
    ...course,
    id: '00000000-0000-0000-0000-000000000002',
    version: '2',
    definition: { ...course.definition, version: '2' },
  };
  let finish: ((value: CurriculumProgress) => void) | undefined;
  vi.mocked(api.setCourseCardProgress).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  vi.mocked(paths.getCurriculum).mockImplementation(async (requested) =>
    requested === id ? course : newer,
  );
  vi.mocked(api.getCourseProgress).mockImplementation(async (requested) =>
    state(false, requested),
  );
  const view = reader();
  fireEvent.click(await screen.findByRole('button', { name: '标记已阅读' }));
  await waitFor(() =>
    expect(api.setCourseCardProgress).toHaveBeenCalledTimes(1),
  );
  const signal = vi.mocked(api.setCourseCardProgress).mock.calls[0]![3];
  view.rerender(
    <QueryClientProvider client={view.cache}>
      <CourseReader courseId={newer.id} onSelectCourse={view.select} />
    </QueryClientProvider>,
  );
  await screen.findByRole('heading', { name: '请求与恢复 · 2' });
  expect(signal.aborted).toBe(true);
  // 课程标题与进度分别读取，先等新课程进度呈现再验证旧写入迟到。
  await screen.findByText('已阅读 0 / 2');
  await act(async () => finish?.(state(true)));
  expect(view.cache.getQueryData(api.courseProgressKey(newer.id, '2'))).toEqual(
    state(false, newer),
  );
  expect(view.cache.getQueryData(api.courseProgressKey(id, '1'))).toEqual(
    state(),
  );
  expect(screen.getByText('已阅读 0 / 2')).toBeTruthy();
});

test('首页仅取第一页前3门发布课程，点击只导航，未激活不读取', async () => {
  const courses = Array.from({ length: 4 }, (_value, index) => ({
    ...course,
    id: `00000000-0000-0000-0000-00000000000${index + 1}`,
    title: `发布课程${index + 1}`,
  }));
  vi.mocked(paths.listCurricula).mockResolvedValue({
    ...empty,
    count: 4,
    results: courses,
  });
  vi.mocked(api.getCourseProgress).mockImplementation(async (requested) =>
    state(false, requested),
  );
  const select = vi.fn();
  render(
    <QueryClientProvider client={client()}>
      <CourseSummary onSelectCourse={select} />
    </QueryClientProvider>,
  );
  await screen.findByRole('button', { name: /发布课程3/ });
  await waitFor(() => expect(api.getCourseProgress).toHaveBeenCalledTimes(3));
  expect(paths.listCurricula).toHaveBeenCalledWith(1, expect.any(AbortSignal));
  expect(screen.queryByRole('button', { name: /发布课程4/ })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /发布课程2/ }));
  expect(select).toHaveBeenCalledWith(courses[1]!.id);
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
  cleanup();
  vi.clearAllMocks();
  const cache = client();
  render(
    <QueryClientProvider client={cache}>
      <CourseSummary active={false} onSelectCourse={select} />
      <CourseReader courseId={id} active={false} onSelectCourse={select} />
    </QueryClientProvider>,
  );
  expect(paths.listCurricula).not.toHaveBeenCalled();
  expect(paths.getCurriculum).not.toHaveBeenCalled();
  expect(api.getCourseProgress).not.toHaveBeenCalled();
  expect(api.getCourseCard).not.toHaveBeenCalled();
});

test('目录分页、空课程和读取错误各自呈现，不误显示成功进度', async () => {
  vi.mocked(paths.listCurricula)
    .mockResolvedValueOnce({
      ...empty,
      count: 2,
      next: '/api/v1/knowledge-curricula/?page=2&page_size=10',
      results: [course],
    })
    .mockResolvedValueOnce(empty);
  reader(null);
  fireEvent.click(await screen.findByRole('button', { name: '下一批记录' }));
  await screen.findByText('暂无已发布课程。');
  expect(paths.listCurricula).toHaveBeenLastCalledWith(
    2,
    expect.any(AbortSignal),
  );
  cleanup();
  vi.mocked(paths.listCurricula).mockRejectedValue(
    new ApiError('课程目录读取失败', 503),
  );
  vi.mocked(paths.getCurriculum).mockRejectedValue(
    new ApiError('所选课程不存在', 404),
  );
  reader();
  await screen.findByText('课程目录读取失败');
  await screen.findByText('所选课程不存在');
  expect(screen.queryByText('已阅读 0 / 2')).toBeNull();
  expect(api.setCourseCardProgress).not.toHaveBeenCalled();
});
