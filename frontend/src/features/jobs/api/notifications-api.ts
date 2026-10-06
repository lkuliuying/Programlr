import { patchJson, requestJson } from '../../../shared/api/client';
import * as v from '../../../shared/api/validation';
import { parseJob } from './jobs-api';
import type {
  Notification,
  NotificationPage,
  PatchedNotificationReadInputRequest,
  PatchedNotificationReadStateInputRequest,
} from '../../../shared/api/generated/schema';

export function parseNotification(value: unknown): Notification {
  const item = v.object(value),
    job = parseJob(item.job);
  if (!['succeeded', 'failed'].includes(job.status)) return v.invalid();
  return { job, read: v.boolean(item.read) };
}
export function parseNotifications(value: unknown): NotificationPage {
  const item = v.object(value);
  return {
    ...v.page(value, '/api/v1/notifications/', parseNotification),
    unread_count: v.integer(item.unread_count),
    as_of: v.date(item.as_of),
    read_through: v.nullable(item.read_through, v.date),
  };
}
export const listNotifications = (page: number, signal: AbortSignal) =>
  requestJson(
    `/api/v1/notifications/?page=${page}&page_size=20`,
    parseNotifications,
    { signal },
  );
export const readNotification = (id: string, signal: AbortSignal) =>
  patchJson(
    `/api/v1/notifications/${id}/`,
    (value) => {
      const result = parseNotification(value);
      return result.job.id === id && result.read ? result : v.invalid();
    },
    { read: true } satisfies PatchedNotificationReadInputRequest,
    signal,
  );
export const readAllNotifications = (
  readThrough: string,
  signal: AbortSignal,
) =>
  patchJson(
    '/api/v1/notification-read-state/',
    (
      value,
    ): Pick<NotificationPage, 'read_through' | 'unread_count' | 'as_of'> => {
      const item = v.object(value);
      const result = {
        read_through: v.date(item.read_through),
        unread_count: v.integer(item.unread_count),
        as_of: v.date(item.as_of),
      };
      return Date.parse(result.read_through) >= Date.parse(readThrough)
        ? result
        : v.invalid();
    },
    {
      read_through: readThrough,
    } satisfies PatchedNotificationReadStateInputRequest,
    signal,
  );
