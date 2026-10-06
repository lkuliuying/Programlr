import { afterEach, expect, test, vi } from 'vitest';
import type {
  KnowledgeCurriculum,
  KnowledgeCard,
} from '../../../shared/api/generated/schema';
import { ApiError } from '../../../shared/api/client';
import {
  getCourseCard,
  getCourseProgress,
  parseCourseProgress,
  setCourseCardProgress,
} from './course-api';

const course: KnowledgeCurriculum = {
  id: '00000000-0000-0000-0000-000000000001',
  slug: 'course',
  version: '1',
  title: '发布课程',
  content_digest: 'a'.repeat(64),
  definition: {
    slug: 'course',
    version: '1',
    title: '发布课程',
    example_version: 'task-board/1.0.0',
    review_note: '固定教学安排',
    nodes: [
      { slug: 'request', card_version: '1' },
      { slug: 'recovery', card_version: '2' },
    ],
    edges: [{ prerequisite: 'request', dependent: 'recovery' }],
    goals: { basics: ['recovery'] },
  },
};
const cards = [
  {
    card_id: '00000000-0000-0000-0000-000000000011',
    slug: 'request',
    version: '1',
    title: '请求边界',
    completed: false,
  },
  {
    card_id: '00000000-0000-0000-0000-000000000012',
    slug: 'recovery',
    version: '2',
    title: '未知结果恢复',
    completed: false,
  },
];
const initial = {
  curriculum_id: course.id,
  version: course.version,
  completed_count: 0,
  total_count: 2,
  cards,
};
const response = (value: unknown) =>
  new Response(JSON.stringify(value), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
afterEach(() => vi.unstubAllGlobals());

test('零进度和真实已阅读计数按课程版本、节点顺序完整校验', () => {
  expect(parseCourseProgress(initial, course)).toEqual(initial);
  const marked = {
    ...initial,
    completed_count: 1,
    cards: cards.map((card, index) => ({ ...card, completed: index === 0 })),
  };
  expect(parseCourseProgress(marked, course).completed_count).toBe(1);
});

test.each([
  { ...initial, curriculum_id: cards[0]!.card_id },
  { ...initial, version: '2' },
  { ...initial, total_count: 1 },
  { ...initial, completed_count: 1 },
  { ...initial, cards: [...cards].reverse() },
  {
    ...initial,
    cards: [cards[0], { ...cards[1], card_id: cards[0]!.card_id }],
  },
  { ...initial, cards: [{ ...cards[0], version: '2' }, cards[1]] },
  { ...initial, cards: [{ ...cards[0], completed: 'true' }, cards[1]] },
])('课程错位、版本漂移、无效计数和重复卡片均拒绝', (raw) => {
  expect(() => parseCourseProgress(raw, course)).toThrow(ApiError);
});

test('读取进度只发 GET，标记和撤销均显式 PATCH 且保持 CSRF 请求边界', async () => {
  let saved = initial;
  const fetchMock = vi.fn<typeof fetch>(async (input, options) => {
    if (String(input) === '/api/v1/csrf/')
      return response({ csrf_token: 'synthetic-csrf' });
    if (options?.method === 'PATCH') {
      const body = JSON.parse(options.body as string) as { completed: boolean };
      saved = {
        ...initial,
        completed_count: body.completed ? 1 : 0,
        cards: cards.map((card, index) => ({
          ...card,
          completed: index === 0 && body.completed,
        })),
      };
    }
    return response(saved);
  });
  vi.stubGlobal('fetch', fetchMock);
  const signal = new AbortController().signal;
  await getCourseProgress(course, signal);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0]![0]).toBe(
    `/api/v1/knowledge-curricula/${course.id}/progress/`,
  );
  expect(fetchMock.mock.calls[0]![1]?.method).toBeUndefined();
  await setCourseCardProgress(course, cards[0]!, true, signal);
  await setCourseCardProgress(course, cards[0]!, false, signal);
  const writes = fetchMock.mock.calls.filter(
    (call) => call[1]?.method === 'PATCH',
  );
  expect(writes).toHaveLength(2);
  expect(writes.map((call) => JSON.parse(call[1]!.body as string))).toEqual([
    { completed: true },
    { completed: false },
  ]);
  expect(writes[0]![0]).toBe(
    `/api/v1/knowledge-curricula/${course.id}/progress/${cards[0]!.card_id}/`,
  );
  expect(
    (writes[0]![1]!.headers as Record<string, string>)['X-CSRFToken'],
  ).toBe('synthetic-csrf');
  expect(fetchMock.mock.calls.some((call) => call[1]?.method === 'POST')).toBe(
    false,
  );
});

test('卡片读取核对精确 ID、slug 和版本，不以其他版本正文代替', async () => {
  const card: KnowledgeCard = {
    id: cards[0]!.card_id,
    slug: 'request',
    version: '1',
    title: '请求边界',
    body: '完整发布正文',
    applicability: '通用知识',
    review_note: '固定内容',
  };
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(response(card))
    .mockResolvedValueOnce(response({ ...card, version: '2' }));
  vi.stubGlobal('fetch', fetchMock);
  expect(await getCourseCard(cards[0]!, new AbortController().signal)).toEqual(
    card,
  );
  await expect(
    getCourseCard(cards[0]!, new AbortController().signal),
  ).rejects.toThrow(ApiError);
  expect(fetchMock.mock.calls[0]![0]).toBe(
    `/api/v1/knowledge-cards/${card.id}/`,
  );
});

test('连接未知只尝试一次写入，响应未反映目标状态也不能冒称保存成功', async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' }))
    .mockRejectedValueOnce(new TypeError('synthetic-network'));
  vi.stubGlobal('fetch', fetchMock);
  await expect(
    setCourseCardProgress(
      course,
      cards[0]!,
      true,
      new AbortController().signal,
    ),
  ).rejects.toThrow(ApiError);
  expect(
    fetchMock.mock.calls.filter((call) => call[1]?.method === 'PATCH'),
  ).toHaveLength(1);
  fetchMock
    .mockResolvedValueOnce(response({ csrf_token: 'synthetic-csrf' }))
    .mockResolvedValueOnce(response(initial));
  await expect(
    setCourseCardProgress(
      course,
      cards[0]!,
      true,
      new AbortController().signal,
    ),
  ).rejects.toThrow(ApiError);
});

test('课程外卡片和非布尔写入在发送前拒绝，精确卡片ID错位不接受', async () => {
  const fetchMock = vi.fn<typeof fetch>();
  vi.stubGlobal('fetch', fetchMock);
  expect(() =>
    setCourseCardProgress(
      course,
      { ...cards[0]!, slug: 'foreign' },
      true,
      new AbortController().signal,
    ),
  ).toThrow(ApiError);
  expect(() =>
    setCourseCardProgress(
      course,
      cards[0]!,
      'true' as unknown as boolean,
      new AbortController().signal,
    ),
  ).toThrow(ApiError);
  expect(fetchMock).not.toHaveBeenCalled();
  const other: KnowledgeCard = {
    id: cards[1]!.card_id,
    slug: 'request',
    version: '1',
    title: '请求边界',
    body: '错误卡片ID',
    applicability: '通用知识',
    review_note: '固定内容',
  };
  fetchMock.mockResolvedValueOnce(response(other));
  await expect(
    getCourseCard(cards[0]!, new AbortController().signal),
  ).rejects.toThrow(ApiError);
});
