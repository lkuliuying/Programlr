import type { Error as ErrorDto } from './generated/schema';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
    readonly code?: ErrorDto['code'],
    readonly details: ErrorDto['details'] = {},
  ) {
    super(message);
  }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isErrorBody(value: unknown): value is ErrorDto {
  if (
    !isRecord(value) ||
    typeof value.code !== 'string' ||
    !/^[A-Z][A-Z0-9_]*$/.test(value.code) ||
    typeof value.message !== 'string' ||
    typeof value.request_id !== 'string' ||
    !value.request_id ||
    !isRecord(value.details)
  )
    return false;
  const fields = value.details.fields;
  return (
    fields === undefined ||
    (isRecord(fields) &&
      Object.values(fields).every(
        (messages) =>
          Array.isArray(messages) &&
          messages.every((message) => typeof message === 'string'),
      ))
  );
}

export async function requestJson<T>(
  path: string,
  decode: (value: unknown) => T,
  options: RequestInit = {},
): Promise<T> {
  if (!path.startsWith('/api/v1/') || path.includes('\\') || path.includes('#'))
    throw new ApiError('接口地址无效。', 0);
  const timeout = AbortSignal.timeout(10000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  let response: Response;
  try {
    response = await fetch(path, {
      ...options,
      signal,
      credentials: 'same-origin',
      redirect: 'error',
      cache: 'no-store',
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      '连接未完成，提交结果可能尚未确定；请保留本次操作并恢复查询。',
      0,
    );
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      '服务入口未返回有效数据，请检查本地服务。',
      response.status,
    );
  }
  if (!response.ok) {
    if (isErrorBody(data)) {
      throw new ApiError(
        data.message,
        response.status,
        data.request_id,
        data.code,
        data.details,
      );
    }
    throw new ApiError('请求失败，服务响应格式无效。', response.status);
  }
  return decode(data);
}

export async function submitJson<T>(
  path: string,
  key: string,
  decode: (value: unknown) => T,
  body: unknown = {},
  signal?: AbortSignal,
): Promise<T> {
  return submitBody(path, key, decode, JSON.stringify(body), signal);
}

export async function submitBody<T>(
  path: string,
  key: string,
  decode: (value: unknown) => T,
  body: string | FormData,
  signal?: AbortSignal,
): Promise<T> {
  return writeBody(path, decode, body, 'POST', signal, key);
}

export async function patchJson<T>(
  path: string,
  decode: (value: unknown) => T,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return writeBody(path, decode, JSON.stringify(body), 'PATCH', signal);
}

export async function deleteJson<T>(
  path: string,
  key: string,
  decode: (value: unknown) => T,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return writeBody(path, decode, JSON.stringify(body), 'DELETE', signal, key);
}

async function writeBody<T>(
  path: string,
  decode: (value: unknown) => T,
  body: string | FormData,
  method: 'POST' | 'PATCH' | 'DELETE',
  signal?: AbortSignal,
  key?: string,
): Promise<T> {
  const token = await requestJson(
    '/api/v1/csrf/',
    (value) => {
      if (!isRecord(value) || typeof value.csrf_token !== 'string')
        throw new ApiError('请求令牌响应无效。', 0);
      return value.csrf_token;
    },
    { signal },
  );
  return requestJson(path, decode, {
    method,
    signal,
    headers: {
      ...(typeof body === 'string'
        ? { 'Content-Type': 'application/json' }
        : {}),
      'X-CSRFToken': token,
      ...(key ? { 'Idempotency-Key': key } : {}),
    },
    body,
  });
}
