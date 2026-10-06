import { afterEach, expect, test, vi } from 'vitest';
import {
  listNotifications,
  parseNotifications,
  readAllNotifications,
  readNotification,
} from './notifications-api';
import * as v from '../../../shared/api/validation';

const id = '00000000-0000-0000-0000-000000000001';
const time = '2026-10-03T00:00:00Z';
const job = {
  id,
  kind: 'system_check',
  status: 'succeeded',
  snapshot_id: null,
  previous_job_id: null,
  result_url: `/api/v1/system-checks/${id}/`,
  stage: 'completed',
  progress: null,
  error: null,
  created_at: time,
  updated_at: time,
};
const page = {
  count: 1,
  previous: null,
  next: null,
  unread_count: 1,
  as_of: time,
  read_through: null,
  results: [{ job, read: false }],
};
const response = (value: unknown) => new Response(JSON.stringify(value));
afterEach(() => vi.unstubAllGlobals());

test('通知分页只读取得真实零值与时间边界，q只允许项目和接口分页', async () => {
  expect(parseNotifications({ ...page, unread_count: 0 }).unread_count).toBe(0);
  expect(() =>
    parseNotifications({
      ...page,
      next: '/api/v1/notifications/?page=2&page_size=20&q=x',
    }),
  ).toThrow('归属');
  expect(() =>
    v.page(
      { ...page, next: '/api/v1/snapshots/?page=2&page_size=20&q=x' },
      '/api/v1/snapshots/',
      v.object,
    ),
  ).toThrow('归属');
  expect(
    v.page(
      { ...page, next: '/api/v1/projects/?page=2&page_size=20&q=x' },
      '/api/v1/projects/',
      v.object,
      ['q'],
    ).next,
  ).toContain('q=x');
  expect(
    v.page(
      {
        ...page,
        next: `/api/v1/analyses/${id}/endpoints/?page=2&page_size=20&q=x`,
      },
      `/api/v1/analyses/${id}/endpoints/`,
      v.object,
      ['q'],
    ).next,
  ).toContain('q=x');
  const fetcher = vi.fn<typeof fetch>(async () => response(page));
  vi.stubGlobal('fetch', fetcher);
  await listNotifications(2, new AbortController().signal);
  expect(fetcher).toHaveBeenCalledExactlyOnceWith(
    '/api/v1/notifications/?page=2&page_size=20',
    expect.objectContaining({ credentials: 'same-origin', redirect: 'error' }),
  );
  expect(fetcher.mock.calls[0]?.[1]).not.toHaveProperty('method');
});

test.each([
  { job: { ...job, id: '00000000-0000-0000-0000-000000000002' }, read: true },
  { job, read: false },
])('单条已读PATCH拒绝其他任务或尚未写入的响应', async (result) => {
  const fetcher = vi.fn(async (path: string, options: RequestInit) =>
    path === '/api/v1/csrf/'
      ? response({ csrf_token: 'synthetic' })
      : (() => {
          expect(options.method).toBe('PATCH');
          expect(JSON.parse(String(options.body))).toEqual({ read: true });
          expect(path).toBe(`/api/v1/notifications/${id}/`);
          return response(result);
        })(),
  );
  vi.stubGlobal('fetch', fetcher);
  await expect(
    readNotification(id, new AbortController().signal),
  ).rejects.toThrow('归属');
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('全部已读只提交已取得的as_of，拒绝未达到该边界的响应', async () => {
  const fetcher = vi.fn(async (path: string, options: RequestInit) =>
    path === '/api/v1/csrf/'
      ? response({ csrf_token: 'synthetic' })
      : (() => {
          expect(path).toBe('/api/v1/notification-read-state/');
          expect(options.method).toBe('PATCH');
          expect(JSON.parse(String(options.body))).toEqual({
            read_through: time,
          });
          return response({
            read_through: '2026-10-02T00:00:00Z',
            unread_count: 1,
            as_of: time,
          });
        })(),
  );
  vi.stubGlobal('fetch', fetcher);
  await expect(
    readAllNotifications(time, new AbortController().signal),
  ).rejects.toThrow('归属');
  expect(fetcher).toHaveBeenCalledTimes(2);
});
