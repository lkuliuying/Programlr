import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, requestJson, submitJson } from './client';

afterEach(() => vi.unstubAllGlobals());
test('写请求先取令牌，再携带同一幂等键且不自动重发', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ csrf_token: 'synthetic-test-token' })),
    )
    .mockRejectedValueOnce(new TypeError('network'));
  vi.stubGlobal('fetch', fetcher);
  await expect(
    submitJson('/api/v1/system-checks/', 'operation-test', (value) => value),
  ).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(fetcher.mock.calls[1][1].headers['Idempotency-Key']).toBe(
    'operation-test',
  );
  expect(fetcher.mock.calls[1][1].credentials).toBe('same-origin');
});
test('代理 HTML 错误和非法 JSON 不伪造请求标识', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(new Response('<html>error</html>', { status: 502 })),
  );
  await expect(
    requestJson('/api/v1/jobs/', (value) => value),
  ).rejects.toMatchObject({ status: 502, requestId: undefined });
});
test('拒绝外部地址', async () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  await expect(
    requestJson('https://invalid.example', (value) => value),
  ).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).not.toHaveBeenCalled();
});

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
    requestJson('/api/v1/jobs/', (value) => value),
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
    requestJson('/api/v1/jobs/', (value) => value),
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
      requestJson('/api/v1/jobs/', (value) => value),
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
    requestJson('/api/v1/jobs/', (value) => value, {
      signal: controller.signal,
    }),
  ).rejects.toBe(reason);
  expect(fetcher).toHaveBeenCalledTimes(1);
});
