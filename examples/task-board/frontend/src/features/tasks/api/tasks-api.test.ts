import { afterEach, expect, test, vi } from 'vitest';
import { createTask, decodeTask, listTasks } from './tasks-api';

afterEach(() => vi.unstubAllGlobals());
test.each([
  null,
  [],
  { id: [], title: '标题', created_at: 'today' },
  {
    id: '12345678-1234-4234-8234-123456789abc',
    title: '  ',
    created_at: '2026-09-29T00:00:00Z',
  },
])('拒绝畸形任务 %#', (value) => {
  expect(() => decodeTask(value)).toThrow();
});
test('拒绝外部翻页链接', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            count: 0,
            results: [],
            next: 'https://evil.invalid',
            previous: null,
          }),
        ),
    ),
  );
  await expect(listTasks(1)).rejects.toThrow('列表响应结构无效。');
});
test('不完整成功响应保留结果未知语义', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) =>
      path.endsWith('/csrf/')
        ? new Response(JSON.stringify({ csrf_token: 'test-only-token' }))
        : new Response('broken', { status: 201 }),
    ),
  );
  await expect(createTask('标题', 'test-key')).rejects.toMatchObject({
    status: 0,
  });
});
