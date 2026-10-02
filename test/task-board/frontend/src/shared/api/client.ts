import type { Error as ErrorDto } from './generated/schema';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status = 0,
    readonly fields: Record<string, string[]> = {},
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
  send: (signal: AbortSignal) => Promise<Response>,
  decode: (value: unknown) => T,
  signal?: AbortSignal,
): Promise<T> {
  const timeout = AbortSignal.timeout(10000);
  let response: Response;
  try {
    response = await send(
      signal ? AbortSignal.any([signal, timeout]) : timeout,
    );
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      '连接未完成。若已提交，请使用原操作恢复，避免重复创建。',
    );
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError('服务响应不完整，提交结果尚不确定。');
  }
  if (!response.ok) {
    if (isErrorBody(data)) {
      const fields: Record<string, string[]> = {};
      if (isRecord(data.details) && isRecord(data.details.fields)) {
        for (const [name, messages] of Object.entries(data.details.fields)) {
          if (
            Array.isArray(messages) &&
            messages.every((item): item is string => typeof item === 'string')
          )
            fields[name] = messages;
        }
      }
      throw new ApiError(
        data.message,
        response.status,
        fields,
        data.request_id,
        data.code,
        data.details,
      );
    }
    throw new ApiError('请求失败，服务响应格式无效。');
  }
  return decode(data);
}

export async function getCsrfToken(signal?: AbortSignal): Promise<string> {
  return requestJson(
    (requestSignal) =>
      fetch('/api/v1/csrf/', {
        signal: requestSignal,
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
      }),
    (value) => {
      if (
        !isRecord(value) ||
        typeof value.csrf_token !== 'string' ||
        !value.csrf_token
      )
        throw new ApiError('请求令牌响应无效。');
      return value.csrf_token;
    },
    signal,
  );
}
