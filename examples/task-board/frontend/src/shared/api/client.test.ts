import { afterEach, expect, test, vi } from 'vitest';
import { requestJson } from './client';

afterEach(() => vi.unstubAllGlobals());

const errorBody = {
  code: 'VALIDATION_ERROR',
  message: '请求参数不符合要求。',
  details: { fields: { title: ['此字段不能为空。'] } },
  request_id: 'request-example',
};

test('完整错误保留机器码、字段明细与服务端请求标识', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(errorBody), { status: 400 }),
      ),
  );
  await expect(
    requestJson(
      (signal) => fetch('/api/v1/tasks/', { signal }),
      (value) => value,
    ),
  ).rejects.toMatchObject({
    status: 400,
    code: 'VALIDATION_ERROR',
    details: errorBody.details,
    requestId: 'request-example',
  });
});

test.each([
  null,
  { ...errorBody, code: undefined },
  { ...errorBody, details: [] },
  { ...errorBody, details: { fields: { title: '非法字段错误' } } },
  { ...errorBody, request_id: '' },
])('畸形错误不冒充服务端协议 %#', async (body) => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify(body), { status: 400 })),
  );
  await expect(
    requestJson(
      (signal) => fetch('/api/v1/tasks/', { signal }),
      (value) => value,
    ),
  ).rejects.toMatchObject({ code: undefined, requestId: undefined });
});

test('HTML 和网络中断均不伪造服务端机器码', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(new Response('<html>error</html>', { status: 502 }))
    .mockRejectedValueOnce(new TypeError('network'));
  vi.stubGlobal('fetch', fetcher);
  for (let i = 0; i < 2; i++) {
    await expect(
      requestJson(
        (signal) => fetch('/api/v1/tasks/', { signal }),
        (value) => value,
      ),
    ).rejects.toMatchObject({ code: undefined, requestId: undefined });
  }
  expect(fetcher).toHaveBeenCalledTimes(2);
});

test('主动取消保持取消语义且不重试', async () => {
  const controller = new AbortController();
  controller.abort();
  const reason = new DOMException('已取消', 'AbortError');
  const fetcher = vi.fn().mockRejectedValue(reason);
  vi.stubGlobal('fetch', fetcher);
  await expect(
    requestJson(
      (signal) => fetch('/api/v1/tasks/', { signal }),
      (value) => value,
      controller.signal,
    ),
  ).rejects.toBe(reason);
  expect(fetcher).toHaveBeenCalledTimes(1);
});
