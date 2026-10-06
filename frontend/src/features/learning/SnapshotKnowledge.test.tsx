import type { ComponentProps } from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnapshotKnowledge } from './SnapshotKnowledge';

const snapshot = '11111111-1111-4111-8111-111111111111';
const scan = '22222222-2222-4222-8222-222222222222';
const historicalScan = '33333333-3333-4333-8333-333333333333';
const analysis = '44444444-4444-4444-8444-444444444444';
const card = {
  id: '55555555-5555-4555-8555-555555555555',
  slug: 'python-comprehensions',
  version: '1.1.0',
  title: '推导式知识卡片',
  body: '推导式把循环与筛选写为一个表达式，结合命中源码核对。',
  applicability: '命中 Python 推导式时适用。',
  review_note: '本轮规则卡片编写与源码核对。',
};
const reference = {
  snapshot_id: snapshot,
  file_path: 'app/views.py',
  start_line: 4,
  end_line: 4,
};
const mapped = {
  concept_key: card.slug,
  card,
  mapped: true,
  hit_count: 1,
  hits: [{ reason: 'python.comprehension', source_ref: reference }],
  package: null,
};
const unknown = {
  concept_key: 'package:mysterious',
  card: null,
  mapped: false,
  hit_count: 1,
  hits: [{ reason: 'python.import_use', source_ref: reference }],
  package: { name: 'mysterious', kind: 'unknown', distribution: null },
};
const response = (value: unknown) => new Response(JSON.stringify(value));
const clients: QueryClient[] = [];
function page(overrides: Record<string, unknown> = {}) {
  return {
    count: 2,
    next: null,
    previous: null,
    results: [mapped, unknown],
    scan_id: scan,
    rule_version: 'source-knowledge/1.0.0',
    coverage: {
      python_files: 2,
      parsed_files: 2,
      syntax_failed_files: 0,
      hit_count: 1,
      package_count: 1,
      complete: true,
      truncated: false,
    },
    diagnostics: [],
    ...overrides,
  };
}
function scanDetail(id = scan, declarations: unknown[] = []) {
  return { id, snapshot_id: snapshot, knowledge: { declarations } };
}
function hitPage() {
  return {
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        concept_key: unknown.concept_key,
        rule_id: 'python.import_use',
        source_ref: reference,
      },
    ],
  };
}
function setup(
  overrides: Partial<ComponentProps<typeof SnapshotKnowledge>> = {},
) {
  const props = {
    snapshotId: snapshot,
    scanId: scan,
    filePath: null,
    analysisId: null,
    endpoint: null,
    onSource: vi.fn(),
    onRescan: vi.fn(),
    ...overrides,
  };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  clients.push(client);
  render(
    <QueryClientProvider client={client}>
      <SnapshotKnowledge {...props} />
    </QueryClientProvider>,
  );
  return props;
}
afterEach(() => {
  cleanup();
  for (const client of clients.splice(0)) client.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('没有接口分析仍读取快照知识，未知导入只列事实并能定位实际来源', async () => {
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    expect(options.method).toBeUndefined();
    if (path.includes('/knowledge-cards/')) return response(page());
    if (path.includes('/knowledge-hits/')) return response(hitPage());
    expect(path).toBe(`/api/v1/source-scans/${scan}/`);
    return response(scanDetail());
  });
  vi.stubGlobal('fetch', fetcher);
  const props = setup();
  await screen.findByRole('button', { name: /mysterious.*未映射/ });
  const firstQuery = new URL(fetcher.mock.calls[0][0], 'http://test.invalid');
  expect(firstQuery.searchParams.get('scan_id')).toBe(scan);
  expect(firstQuery.searchParams.has('analysis_id')).toBe(false);
  expect(screen.getByRole('option', { name: '当前接口' })).toHaveProperty(
    'disabled',
    true,
  );
  fireEvent.click(screen.getByRole('button', { name: /mysterious.*未映射/ }));
  await screen.findByRole('button', { name: 'app/views.py:4–4' });
  expect(screen.getByText(/未生成知识正文/)).toBeTruthy();
  expect(screen.queryByText(card.body)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'app/views.py:4–4' }));
  expect(props.onSource).toHaveBeenCalledWith(reference);
  const hits = fetcher.mock.calls.find(([path]) =>
    path.includes('/knowledge-hits/'),
  )!;
  expect(
    new URL(hits[0], 'http://test.invalid').searchParams.get('concept_key'),
  ).toBe(unknown.concept_key);
  fireEvent.click(screen.getByRole('button', { name: '重新识别知识' }));
  expect(props.onRescan).toHaveBeenCalledOnce();
  expect(fetcher.mock.calls.every(([, options]) => !options.method)).toBe(true);
});

test('文件与接口使用各自精确筛选，接口的历史扫描版本决定依赖来源', async () => {
  const declaration = {
    distribution: 'httpx',
    specifier: '>=0.2',
    conditional: true,
    optional: true,
    source_ref: {
      ...reference,
      file_path: 'requirements-dev.txt',
      start_line: 2,
      end_line: 2,
    },
  };
  const fetcher = vi.fn(async (path: string) => {
    const url = new URL(path, 'http://test.invalid');
    if (path.includes('/knowledge-cards/')) {
      const id = url.searchParams.has('analysis_id') ? historicalScan : scan;
      return response(page({ scan_id: id }));
    }
    if (path.includes('/knowledge-hits/')) return response(hitPage());
    const id = path.includes(historicalScan) ? historicalScan : scan;
    return response(scanDetail(id, id === historicalScan ? [declaration] : []));
  });
  vi.stubGlobal('fetch', fetcher);
  const props = setup({
    filePath: reference.file_path,
    analysisId: analysis,
    endpoint: 3,
  });
  await screen.findByRole('button', { name: /推导式知识卡片/ });
  fireEvent.change(screen.getByLabelText('知识范围'), {
    target: { value: 'file' },
  });
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(([path]) => path.includes('file_path=')),
    ).toBe(true),
  );
  const file = fetcher.mock.calls.find(([path]) =>
    path.includes('file_path='),
  )![0];
  const fileQuery = new URL(file, 'http://test.invalid').searchParams;
  expect(fileQuery.get('file_path')).toBe(reference.file_path);
  expect(fileQuery.get('scan_id')).toBe(scan);
  expect(fileQuery.has('analysis_id')).toBe(false);
  fireEvent.change(screen.getByLabelText('知识范围'), {
    target: { value: 'interface' },
  });
  await screen.findByText('依赖声明事实（1）');
  const interfacePath = fetcher.mock.calls.find(([path]) =>
    path.includes('analysis_id='),
  )![0];
  const interfaceQuery = new URL(interfacePath, 'http://test.invalid')
    .searchParams;
  expect(interfaceQuery.get('analysis_id')).toBe(analysis);
  expect(interfaceQuery.get('endpoint_index')).toBe('3');
  expect(interfaceQuery.has('scan_id')).toBe(false);
  expect(interfaceQuery.has('file_path')).toBe(false);
  expect(fetcher).toHaveBeenCalledWith(
    `/api/v1/source-scans/${historicalScan}/`,
    expect.any(Object),
  );
  fireEvent.click(screen.getByText('依赖声明事实（1）'));
  expect(screen.getByText('httpx>=0.2')).toBeTruthy();
  expect(screen.getByText(/有条件.*可选/)).toBeTruthy();
  fireEvent.click(
    screen.getByRole('button', { name: 'requirements-dev.txt:2' }),
  );
  expect(props.onSource).toHaveBeenCalledWith(declaration.source_ref);
  fireEvent.click(screen.getByRole('button', { name: /推导式知识卡片/ }));
  await screen.findByText(card.body);
  expect(screen.getByText('版本 1.1.0 · 1 处命中')).toBeTruthy();
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([path]) =>
          path.includes('/knowledge-hits/') && path.includes('analysis_id='),
      ),
    ).toBe(true),
  );
});

test('覆盖范围截断和解析诊断明确展示，正文仍只从所选版本化卡片打开', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      if (path.includes('/knowledge-cards/'))
        return response(
          page({
            coverage: {
              python_files: 5,
              parsed_files: 3,
              syntax_failed_files: 1,
              hit_count: 1,
              package_count: 1,
              complete: false,
              truncated: true,
            },
            diagnostics: [
              {
                code: 'KNOWLEDGE_OUTPUT_LIMIT',
                message: '知识结果达到字节上限，部分事实未纳入。',
              },
            ],
          }),
        );
      if (path.includes('/knowledge-hits/')) return response(hitPage());
      return response(scanDetail());
    }),
  );
  setup();
  await screen.findByText(/识别范围有限，结果已截断/);
  expect(screen.getByText(/已解析 3\/5 个 Python 文件/)).toBeTruthy();
  fireEvent.click(screen.getByText('识别诊断（1）'));
  expect(
    screen.getByText('知识结果达到字节上限，部分事实未纳入。'),
  ).toBeTruthy();
  expect(screen.queryByText(card.body)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /推导式知识卡片/ }));
  await screen.findByText(card.body);
  expect(screen.getByText(card.review_note)).toBeTruthy();
});

test('历史快照无扫描时零自动请求，只在显式识别按钮上通知父组件', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  const props = setup({ scanId: null });
  expect(screen.getByText(/旧分析结果不会自动回填/)).toBeTruthy();
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: '重新识别知识' }));
  expect(props.onRescan).toHaveBeenCalledOnce();
  expect(fetcher).not.toHaveBeenCalled();
});

test.each(['mapped', 'reference'])(
  '拒绝%s无效卡片响应，不显示跨资源事实',
  async (invalid) => {
    const entry =
      invalid === 'mapped'
        ? { ...unknown, mapped: true }
        : {
            ...unknown,
            hits: [
              {
                reason: 'python.import',
                source_ref: { ...reference, snapshot_id: historicalScan },
              },
            ],
          };
    const fetcher = vi.fn(async () =>
      response(page({ count: 1, results: [entry] })),
    );
    vi.stubGlobal('fetch', fetcher);
    setup();
    await screen.findByText('响应结构或资源归属无效。');
    expect(screen.queryByRole('button', { name: /mysterious/ })).toBeNull();
    expect(fetcher).toHaveBeenCalledOnce();
  },
);

test('依赖声明拒绝与卡片扫描不一致的扫描身份，保留已校验知识列表', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      if (path.includes('/knowledge-cards/')) return response(page());
      return response(
        scanDetail(historicalScan, [
          {
            distribution: 'forged',
            specifier: '',
            conditional: false,
            optional: false,
            source_ref: reference,
          },
        ]),
      );
    }),
  );
  setup();
  await screen.findByText('响应结构或资源归属无效。');
  expect(screen.getByRole('button', { name: /推导式知识卡片/ })).toBeTruthy();
  expect(screen.queryByText(/依赖声明事实/)).toBeNull();
  expect(screen.queryByText('forged')).toBeNull();
});
