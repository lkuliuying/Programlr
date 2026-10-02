import type { Task, TaskPage } from '../../../shared/api/generated/schema';
import {
  ApiError,
  getCsrfToken,
  isRecord,
  requestJson,
} from '../../../shared/api/client';

export function decodeTask(value: unknown): Task {
  if (
    !isRecord(value) ||
    typeof value.id !== 'string' ||
    !/^[0-9a-f-]{36}$/i.test(value.id) ||
    typeof value.title !== 'string' ||
    !value.title.trim() ||
    Array.from(value.title).length > 200 ||
    typeof value.created_at !== 'string' ||
    !value.created_at.endsWith('Z') ||
    Number.isNaN(Date.parse(value.created_at))
  ) {
    throw new ApiError('任务响应结构无效。');
  }
  return { id: value.id, title: value.title, created_at: value.created_at };
}

function decodePage(value: unknown): TaskPage {
  const validLink = (link: unknown): link is string | null =>
    link === null ||
    (typeof link === 'string' &&
      /^\/api\/v1\/tasks\/\?page=\d+&page_size=\d+$/.test(link));
  if (
    !isRecord(value) ||
    typeof value.count !== 'number' ||
    !Number.isSafeInteger(value.count) ||
    value.count < 0 ||
    !Array.isArray(value.results) ||
    value.results.length > 100 ||
    value.count < value.results.length ||
    !validLink(value.next) ||
    !validLink(value.previous)
  )
    throw new ApiError('列表响应结构无效。');
  return {
    count: value.count,
    next: value.next,
    previous: value.previous,
    results: value.results.map(decodeTask),
  };
}

export function listTasks(
  page: number,
  signal?: AbortSignal,
): Promise<TaskPage> {
  return requestJson(
    (requestSignal) =>
      fetch(`/api/v1/tasks/?page=${page}&page_size=20`, {
        signal: requestSignal,
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
      }),
    decodePage,
    signal,
  );
}

export async function createTask(
  title: string,
  key: string,
  signal?: AbortSignal,
): Promise<Task> {
  const token = await getCsrfToken(signal);
  return requestJson(
    (requestSignal) =>
      fetch('/api/v1/tasks/', {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
        signal: requestSignal,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': token,
          'Idempotency-Key': key,
        },
        body: JSON.stringify({ title }),
      }),
    decodeTask,
    signal,
  );
}
