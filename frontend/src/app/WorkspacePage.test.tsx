import { webcrypto } from 'node:crypto';
import { afterEach, expect, test, vi } from 'vitest';
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkspacePage } from './WorkspacePage';
import { readSelection } from './workspace-location';
import { ThemeProvider } from './ThemeProvider';
import { navigation } from './WorkspaceShell';

const project = '00000000-0000-0000-0000-000000000001',
  snapshot = '00000000-0000-0000-0000-000000000002',
  analysis = '00000000-0000-0000-0000-000000000003',
  job = '00000000-0000-0000-0000-000000000004',
  file = '00000000-0000-0000-0000-000000000005',
  node = '00000000-0000-0000-0000-000000000006';
const time = '2026-09-29T00:00:00Z';
const projectDto = { id: project, name: '任务教学样例', created_at: time };
const snapshotDto = {
  id: snapshot,
  name: '',
  project_id: project,
  job_id: job,
  created_at: time,
  source_extensions: ['.py'],
  summary: {
    entries: 1,
    accepted: 1,
    excluded: 0,
    skipped: 0,
    rejected: 0,
    declared_bytes: 15,
    extracted_bytes: 15,
    reasons: {},
  },
};
const source = {
  id: file,
  snapshot_id: snapshot,
  file_path: 'root_urls.py',
  sha256: 'a'.repeat(64),
  size_bytes: 15,
  line_count: 1,
  encoding: 'utf-8',
};
const reference = {
  snapshot_id: snapshot,
  file_path: 'root_urls.py',
  start_line: 1,
  end_line: 1,
};
const proof = {
  kind: 'source_fact',
  rule: 'synthetic.source',
  source_ref: reference,
};
const coverage = {
  python_files: 1,
  parsed_files: 1,
  syntax_failed_files: 0,
  skipped_files: 0,
  endpoint_count: 1,
  diagnostic_count: 0,
  complete: true,
  limitations: ['仅静态分析'],
};
const detail = {
  id: analysis,
  snapshot_id: snapshot,
  job_id: job,
  root_urlconf: 'root_urls.py',
  rule_version: 'test/1',
  coverage,
  frontend: null,
  created_at: time,
};
const endpoint = {
  index: 0,
  method: 'POST',
  path: '/api/tasks/',
  path_kind: 'django_path',
  action: 'create',
  view: null,
  serializer: null,
  model: null,
  evidence: [proof],
  frontend_available: false,
  frontend_links: [],
};
const graph = {
  analysis_id: analysis,
  snapshot_id: snapshot,
  rule_version: 'test/1',
  graph_version: 'analysis-graph/1.0.0',
  root_node_id: null,
  endpoint_index: null,
  algorithm: 'bfs',
  nodes: [
    {
      id: node,
      kind: 'endpoint',
      name: 'POST /api/tasks/',
      source_ref: reference,
      evidence: [proof],
      endpoint: {
        index: 0,
        method: 'POST',
        path: '/api/tasks/',
        path_kind: 'django_path',
        action: 'create',
        is_candidate: false,
      },
      request: null,
    },
  ],
  edges: [],
  relation_reviews: [],
  coverage,
  diagnostics_url: `/api/v1/analyses/${analysis}/diagnostics/`,
  total_nodes: 1,
  total_edges: 0,
  returned_nodes: 1,
  returned_edges: 0,
  truncated: false,
  truncation_reasons: [],
};
const secondNode = {
  ...graph.nodes[0]!,
  id: '00000000-0000-0000-0000-000000000011',
  name: 'GET /api/task-summary/',
  endpoint: {
    ...graph.nodes[0]!.endpoint,
    index: 1,
    method: 'GET',
    path: '/api/task-summary/',
  },
};
const page = (results: unknown[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
});
const response = (value: unknown) => new Response(JSON.stringify(value));
function task(kind: 'import' | 'analysis') {
  return {
    id: kind === 'import' ? job : '00000000-0000-0000-0000-000000000007',
    kind,
    status: 'succeeded',
    stage: 'completed',
    created_at: time,
    updated_at: time,
    snapshot_id: snapshot,
    previous_job_id: null,
    progress: null,
    error: null,
    result_url:
      kind === 'import'
        ? `/api/v1/snapshots/${snapshot}/`
        : `/api/v1/analyses/${analysis}/`,
  };
}
function reads(path: string): unknown {
  const url = new URL(path, 'http://local.test'),
    route = url.pathname;
  if (route === '/api/v1/projects/') return page([projectDto]);
  if (route === `/api/v1/projects/${project}/`) return projectDto;
  if (route === `/api/v1/projects/${project}/snapshots/`)
    return page([snapshotDto]);
  if (route === `/api/v1/snapshots/${snapshot}/`) return snapshotDto;
  if (route.endsWith('/files/')) return page([source]);
  if (route.endsWith('/content/'))
    return {
      ...source,
      start_line: 1,
      end_line: 1,
      content: 'urlpatterns=[]\n',
    };
  if (route === '/api/v1/jobs/') return page([task('analysis')]);
  if (route === `/api/v1/analyses/${analysis}/`) return detail;
  if (
    /\/(?:knowledge-cards|knowledge-curricula|exercises|exercise-attempts|explanations|lab-runs|system-labs|system-lab-runs|snapshot-comparisons)\/$/.test(
      route,
    )
  )
    return page([]);
  if (route === '/api/v1/labs/request-validation/')
    return {
      id: 'request-validation',
      version: '1',
      title: '请求校验实验',
      example_version: 'task-board/1.0.0',
      description: '合成实验定义，不运行实验。',
      cases: ['normal', 'missing', 'empty', 'whitespace'].map((id) => ({
        id,
        title: id,
        input: {},
      })),
      applicable: false,
      applicability_reason: '合成源码不匹配内置实验。',
    };
  if (route.endsWith('/endpoints/')) return page([endpoint]);
  if (route.endsWith('/diagnostics/')) return page([]);
  if (route.endsWith('/graph/'))
    return {
      ...graph,
      endpoint_index: url.searchParams.has('endpoint_index') ? 0 : null,
    };
  throw new Error(`测试未定义读取 ${route}`);
}
function readTwoEndpointGraph(path: string): unknown {
  const url = new URL(path, 'http://local.test');
  if (url.pathname.endsWith('/graph/')) {
    const selected = url.searchParams.get('endpoint_index');
    const nodes =
      selected === null
        ? [...graph.nodes, secondNode]
        : selected === '0'
          ? graph.nodes
          : [secondNode];
    return {
      ...graph,
      endpoint_index: selected === null ? null : Number(selected),
      nodes,
      total_nodes: nodes.length,
      returned_nodes: nodes.length,
      coverage: { ...coverage, endpoint_count: 2 },
    };
  }
  return reads(path);
}
function show(search = '') {
  window.history.replaceState(null, '', '/' + search);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const view = render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <WorkspacePage />
      </QueryClientProvider>
    </ThemeProvider>,
  );
  return { ...view, client };
}
function expectModule(label: (typeof navigation)[number][1]) {
  expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  expect(screen.getByRole('heading', { level: 1, name: label })).toBeTruthy();
  for (const [, other] of navigation) {
    if (other === label) {
      expect(screen.getByRole('region', { name: `${other}页面` })).toBeTruthy();
      expect(
        screen
          .getByRole('button', { name: other })
          .getAttribute('aria-current'),
      ).toBe('page');
    } else {
      expect(screen.queryByRole('region', { name: `${other}页面` })).toBeNull();
      expect(
        screen
          .getByRole('button', { name: other })
          .getAttribute('aria-current'),
      ).toBeNull();
    }
  }
}
afterEach(() => {
  cleanup();
  sessionStorage.clear();
  localStorage.clear();
  vi.unstubAllGlobals();
});

test('完整入口创建、ZIP、分析、历史源码定位，刷新保留资源选择', async () => {
  vi.stubGlobal('crypto', webcrypto);
  let created = false,
    kind: 'import' | 'analysis' = 'import';
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/')) return response({ csrf_token: 'synthetic' });
      if (options.method === 'POST') {
        expect(new Headers(options.headers).get('Idempotency-Key')).toMatch(
          /^[a-f0-9-]{36}$/,
        );
        if (path === '/api/v1/projects/') {
          created = true;
          return response(projectDto);
        }
        if (path.endsWith('/analyses/')) {
          kind = 'analysis';
          expect(JSON.parse(String(options.body))).toEqual({
            root_urlconf: 'root_urls.py',
          });
        }
        return response(task(kind));
      }
      if (path.startsWith('/api/v1/projects/?') && !created)
        return response(page([]));
      if (/^\/api\/v1\/jobs\/[a-f0-9-]{36}\/$/.test(path))
        return response(task(kind));
      return response(reads(path));
    }),
  );
  const view = show();
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  fireEvent.change(screen.getByLabelText('项目名称'), {
    target: { value: '任务教学样例' },
  });
  fireEvent.click(screen.getByRole('button', { name: '创建项目' }));
  await screen.findByLabelText('导入源码 ZIP');
  const zip = new File(['synthetic zip'], 'sample.zip', {
    type: 'application/zip',
  });
  Object.defineProperty(zip, 'arrayBuffer', {
    value: async () => new TextEncoder().encode('synthetic zip').buffer,
  });
  fireEvent.change(screen.getByLabelText('导入源码 ZIP'), {
    target: { files: [zip] },
  });
  // jsdom 的文件选择不更新原生 required 有效性；提交已填好的表单。
  fireEvent.submit(screen.getByLabelText('导入源码 ZIP').closest('form')!);
  fireEvent.click(await screen.findByRole('button', { name: '查看任务结果' }));
  fireEvent.click(screen.getByRole('button', { name: 'API 分析' }));
  fireEvent.change(await screen.findByLabelText('根路由文件'), {
    target: { value: 'root_urls.py' },
  });
  fireEvent.click(screen.getByRole('button', { name: '提交分析' }));
  fireEvent.click(await screen.findByRole('button', { name: '查看任务结果' }));
  await screen.findByRole('heading', { name: 'API 分析', level: 1 });
  fireEvent.click(
    await within(
      await screen.findByRole('navigation', { name: '接口导航' }),
    ).findByRole('button', { name: /POST/ }),
  );
  expect(
    await within(
      screen.getByRole('region', { name: '接口定义与前端来源' }),
    ).findByText(/此历史记录未分析前端/),
  ).toBeTruthy();
  fireEvent.click(
    await within(
      screen.getByRole('region', { name: '接口定义与前端来源' }),
    ).findByRole('button', { name: 'root_urls.py:1–1' }),
  );
  expect(await screen.findByText('urlpatterns=[]')).toBeTruthy();
  const search = window.location.search;
  expect(readSelection(search).reference).toEqual(reference);
  view.unmount();
  view.client.clear();
  show(search);
  expect(await screen.findByText('urlpatterns=[]')).toBeTruthy();
});

test('快速切换项目时迟到读取不恢复旧源码，前进后退读取 URL', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) =>
      path.endsWith('start_line=1&end_line=1')
        ? new Promise<Response>((resolve) => {
            finish = resolve;
          })
        : response(reads(path)),
    ),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&file=root_urls.py&start=1&end=1`,
  );
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  window.history.pushState(null, '', `?project=${project}`);
  window.dispatchEvent(new PopStateEvent('popstate'));
  await screen.findByRole('heading', { name: '工作台', level: 1 });
  finish(
    response({
      ...source,
      start_line: 1,
      end_line: 1,
      content: '旧源码不应出现\n',
    }),
  );
  await waitFor(() => expect(screen.queryByText('旧源码不应出现')).toBeNull());
  act(() => {
    window.history.pushState(
      null,
      '',
      `?project=${project}&snapshot=${snapshot}`,
    );
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  fireEvent.click(screen.getByRole('button', { name: 'API 分析' }));
  await screen.findByLabelText('根路由文件');
});

test('地址缺失归属或带重复参数时阻止错误资源查询', () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  show(`?snapshot=${snapshot}`);
  expect(screen.getByRole('alert').textContent).toContain('参数缺失');
  expect(fetcher).not.toHaveBeenCalled();
  expect(
    readSelection(`?project=${project}&snapshot=${snapshot}&endpoint=1`)
      .invalid,
  ).toBe(true);
  expect(readSelection(`?project=${project}&project=${project}`).invalid).toBe(
    true,
  );
});

test('候选、未匹配与截断图均明确展示，不伪装为确认链路', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      if (path.includes('/graph/'))
        return response({
          ...graph,
          graph_version: 'analysis-graph/2.0.0',
          nodes: [
            {
              id: node,
              kind: 'frontend_request',
              name: '候选请求',
              source_ref: reference,
              evidence: [proof],
              endpoint: null,
              request: {
                method: 'POST',
                original_path: '/tasks/',
                path: '/tasks/',
                status: 'candidate',
                reason: 'unknown_base',
              },
            },
          ],
          truncated: true,
          truncation_reasons: ['max_nodes'],
          total_nodes: 200,
        });
      return response(reads(path));
    }),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&section=graph`,
  );
  const overview = await screen.findByRole('region', { name: '静态关系图' });
  fireEvent.click(
    await within(overview).findByRole('button', { name: /候选请求/ }),
  );
  expect(await within(overview).findByText(/基础地址未知/)).toBeTruthy();
  expect(within(overview).getByText(/结果已截断/)).toBeTruthy();
  expect(screen.queryByText('静态确认')).toBeNull();
});

test('创建结果未知时用相同标识恢复，切换后迟到提交不跳回', async () => {
  vi.stubGlobal('crypto', webcrypto);
  const keys: string[] = [];
  let finish!: (value: Response) => void;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (path.endsWith('/csrf/')) return response({ csrf_token: 'synthetic' });
      if (options.method === 'POST') {
        keys.push(new Headers(options.headers).get('Idempotency-Key')!);
        if (keys.length === 1) throw new TypeError('network');
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      }
      return response(reads(path));
    }),
  );
  const first = show();
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  fireEvent.change(screen.getByLabelText('项目名称'), {
    target: { value: '待确认' },
  });
  fireEvent.click(screen.getByRole('button', { name: '创建项目' }));
  await screen.findByRole('alert');
  first.unmount();
  first.client.clear();
  show();
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  fireEvent.change(screen.getByLabelText('项目名称'), {
    target: { value: '待确认' },
  });
  fireEvent.click(screen.getByRole('button', { name: '恢复创建项目' }));
  await waitFor(() => expect(keys).toHaveLength(2));
  expect(keys[0]).toBe(keys[1]);
  fireEvent.click(await screen.findByRole('button', { name: '任务教学样例' }));
  await screen.findByLabelText('导入源码 ZIP');
  finish(response({ ...projectDto, id: snapshot }));
  await waitFor(() =>
    expect(new URLSearchParams(window.location.search).get('project')).toBe(
      project,
    ),
  );
});

test('同一快照打开旧讲解立即切换面板，引用与刷新仍定位原源码', async () => {
  const explanation = '00000000-0000-0000-0000-000000000008';
  const explanationDto = {
    id: explanation,
    job_id: job,
    preview_id: file,
    analysis_id: analysis,
    snapshot_id: snapshot,
    endpoint_index: 0,
    template_version: 'explanation/1.0.0',
    model: 'synthetic-history',
    usage: null,
    content: Object.fromEntries(
      ['purpose', 'evidence', 'mechanism', 'knowledge', 'verification'].map(
        (name) => [
          name,
          [
            {
              kind: 'source_fact',
              text: '合成旧讲解',
              source_refs: [reference],
            },
          ],
        ],
      ),
    ),
    created_at: time,
  };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      if (path === `/api/v1/explanations/${explanation}/`)
        return response(explanationDto);
      if (path.startsWith('/api/v1/explanations/?'))
        return response(page([explanationDto]));
      return response(reads(path));
    }),
  );
  const first = show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0`,
  );
  await screen.findByRole('heading', { name: '工作台', level: 1 });
  window.history.pushState(
    null,
    '',
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&explanation=${explanation}&candidates=true`,
  );
  window.dispatchEvent(new PopStateEvent('popstate'));
  await screen.findByRole('heading', { name: '模型讲解', level: 1 });
  const panel = await screen.findByRole('region', { name: '源码讲解' });
  fireEvent.click(
    (
      await within(panel).findAllByRole('button', { name: 'root_urls.py:1–1' })
    )[0]!,
  );
  await screen.findByRole('heading', { name: '源码阅读', level: 1 });
  expect(await screen.findByText('urlpatterns=[]')).toBeTruthy();
  const search = window.location.search;
  expect(readSelection(search).reference).toEqual(reference);
  expect(readSelection(search).candidates).toBe(true);
  first.unmount();
  first.client.clear();
  show(search);
  await screen.findByRole('heading', { name: '源码阅读', level: 1 });
  expect(await screen.findByText('urlpatterns=[]')).toBeTruthy();
});

test('学习目标保留时实验面板刷新及前进后退恢复显式选择', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => response(reads(path))),
  );
  const first = show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&goal=create-task`,
  );
  await screen.findByRole('heading', { name: '知识与学习', level: 1 });
  fireEvent.click(screen.getByRole('button', { name: '练习与实验' }));
  const panels = await screen.findByRole('navigation', {
    name: '练习与实验内容',
  });
  fireEvent.click(within(panels).getByRole('button', { name: '受控实验' }));
  await screen.findByRole('button', { name: '受控实验', pressed: true });
  const search = window.location.search;
  expect(readSelection(search).panel).toBe('lab');
  expect(readSelection(search).goal).toBe('create-task');
  fireEvent.click(screen.getByRole('button', { name: '固定练习与复习' }));
  await screen.findByRole('button', { name: '固定练习与复习', pressed: true });
  window.history.pushState(null, '', search);
  window.dispatchEvent(new PopStateEvent('popstate'));
  await screen.findByRole('button', { name: '受控实验', pressed: true });
  first.unmount();
  first.client.clear();
  show(search);
  await screen.findByRole('button', { name: '受控实验', pressed: true });
  window.history.pushState(
    null,
    '',
    search
      .replace('panel=lab', 'panel=learning')
      .replace('section=labs', 'section=learning'),
  );
  window.dispatchEvent(new PopStateEvent('popstate'));
  await screen.findByRole('heading', { name: '知识与学习', level: 1 });
  window.history.pushState(null, '', search);
  window.dispatchEvent(new PopStateEvent('popstate'));
  await screen.findByRole('button', { name: '受控实验', pressed: true });
  for (const suffix of [
    'panel=unknown',
    'panel=lab&panel=learning',
    'panel=lab',
  ]) {
    const prefix =
      suffix === 'panel=lab'
        ? ''
        : `project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&`;
    expect(readSelection(`?${prefix}${suffix}`).invalid).toBe(true);
  }
});

test('从学习上下文返回全图时清理接口专属记录，保留同快照固定文件', async () => {
  const fetcher = vi.fn(async (path: string) => response(reads(path)));
  vi.stubGlobal('fetch', fetcher);
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&goal=create-task&panel=learning&file2=root_urls.py&start2=1&end2=1`,
  );
  await screen.findByRole('heading', { name: '知识与学习', level: 1 });
  fireEvent.click(screen.getByRole('button', { name: '静态关系图' }));
  const current = within(
    await screen.findByRole('region', { name: '静态关系图' }),
  );
  fireEvent.click(await current.findByRole('button', { name: '查看全图' }));
  await waitFor(() =>
    expect(readSelection(window.location.search).endpoint).toBeNull(),
  );
  const selected = readSelection(window.location.search);
  expect(selected.invalid).toBe(false);
  expect(selected.goal).toBeNull();
  expect(selected.panel).toBeNull();
  expect(selected.secondaryReference).toEqual(reference);
});

test('接口范围返回全图后点击接口节点保持全图，不发起新的接口范围请求', async () => {
  const fetcher = vi.fn(async (path: string) =>
    response(readTwoEndpointGraph(path)),
  );
  vi.stubGlobal('fetch', fetcher);
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=graph`,
  );
  const current = within(
    await screen.findByRole('region', { name: '静态关系图' }),
  );
  fireEvent.click(await current.findByRole('button', { name: '查看全图' }));
  const target = await current.findByRole('button', {
    name: /^GET \/api\/task-summary\//,
  });
  expect(readSelection(window.location.search).endpoint).toBeNull();
  const scopedRequests = fetcher.mock.calls
    .map(([path]) => path)
    .filter(
      (path) => path.includes('/graph/') && path.includes('endpoint_index='),
    );
  expect(scopedRequests).toHaveLength(1);
  expect(scopedRequests[0]).toContain('endpoint_index=0');
  fireEvent.click(target);
  await waitFor(() => {
    const selected = readSelection(window.location.search);
    expect(selected.invalid).toBe(false);
    expect(selected.endpoint).toBeNull();
    expect(selected.node).toBe(secondNode.id);
    expect(selected.section).toBe('graph');
  });
  expect(new URLSearchParams(window.location.search).has('endpoint')).toBe(
    false,
  );
  expect(
    current.getByRole('button', { name: /^POST \/api\/tasks\// }),
  ).toBeTruthy();
  expect(
    current.getByRole('button', { name: /^GET \/api\/task-summary\// }),
  ).toHaveProperty('ariaPressed', 'true');
  expect(current.getByText(/全图范围/)).toBeTruthy();
  expect(current.queryByRole('button', { name: '查看全图' })).toBeNull();
  expect(
    fetcher.mock.calls
      .map(([path]) => path)
      .filter(
        (path) => path.includes('/graph/') && path.includes('endpoint_index='),
      ),
  ).toEqual(scopedRequests);
});

test('接口范围图跨接口选择仍清理旧接口记录，保留同快照源码引用', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      const url = new URL(path, 'http://local.test');
      const route = url.pathname;
      if (route === `/api/v1/jobs/${job}/`)
        return response({ ...task('analysis'), id: job });
      if (
        /^\/api\/v1\/(?:context-previews|explanations|exercise-attempts|lab-runs|system-lab-runs|knowledge-curricula)\/[a-f0-9-]{36}\/$/.test(
          route,
        )
      )
        return new Response(
          JSON.stringify({
            code: 'NOT_FOUND',
            message: '旧接口记录不存在。',
            request_id: 'synthetic-old-endpoint',
            details: {},
          }),
          { status: 404 },
        );
      if (route.endsWith('/graph/'))
        return response({
          ...graph,
          endpoint_index: url.searchParams.has('endpoint_index')
            ? Number(url.searchParams.get('endpoint_index'))
            : null,
          nodes: [...graph.nodes, secondNode],
          total_nodes: 2,
          returned_nodes: 2,
          coverage: { ...coverage, endpoint_count: 2 },
        });
      return response(reads(path));
    }),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=graph&preview=${file}&explanation=${node}&attempt=${job}&run=${file}&system_run=${node}&curriculum=${file}&goal=create-task&panel=learning&job=${job}&file2=root_urls.py&start2=1&end2=1`,
  );
  fireEvent.click(
    await within(
      await screen.findByRole('region', { name: '静态关系图' }),
    ).findByRole('button', {
      name: /^GET \/api\/task-summary\//,
    }),
  );
  await waitFor(() =>
    expect(readSelection(window.location.search).endpoint).toBe(1),
  );
  const selected = readSelection(window.location.search);
  expect(selected.invalid).toBe(false);
  expect(selected.node).toBe(secondNode.id);
  expect(selected.section).toBe('graph');
  for (const key of [
    'preview',
    'explanation',
    'attempt',
    'run',
    'system_run',
    'curriculum',
    'goal',
    'panel',
    'job',
  ] as const)
    expect(selected[key]).toBeNull();
  expect(selected.secondaryReference).toEqual(reference);
  expect(await screen.findByRole('button', { name: '查看全图' })).toBeTruthy();
});

test('无项目时 12 个模块各自显示唯一页面与专属引导', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => response(reads(path))),
  );
  show();
  for (const [, label] of navigation) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    const current = screen.getByRole('region', { name: `${label}页面` });
    if (
      [
        '源码阅读',
        'API 分析',
        '静态关系图',
        '快照与对比',
        '候选影响',
        '练习与实验',
        '模型讲解',
      ].includes(label)
    ) {
      expect(
        within(current).getByText(`${label}需要先打开一个项目。`),
      ).toBeTruthy();
      expect(
        within(current).getByRole('button', { name: '前往项目导入' }),
      ).toBeTruthy();
    }
    if (label === '项目导入')
      expect(
        within(current).getByRole('textbox', { name: '项目名称' }),
      ).toBeTruthy();
    if (label === '知识与学习')
      expect(
        within(current).getByRole('region', { name: '知识卡片' }),
      ).toBeTruthy();
    if (label === '系统状态')
      expect(
        within(current).getByRole('button', { name: '开始基础检查' }),
      ).toBeTruthy();
  }
});

test.each(['?section=jobs', '?view=jobs&page=2'])(
  '任务入口 %s 不包含系统检查表单',
  async (search) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (path: string) => response(reads(path))),
    );
    show(search);
    expectModule('任务历史');
    await screen.findByText('源码分析');
    expect(screen.queryByRole('button', { name: '开始基础检查' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '系统状态' }));
    expectModule('系统状态');
    expect(screen.getByRole('button', { name: '开始基础检查' })).toBeTruthy();
    expect(screen.queryByRole('region', { name: '任务记录' })).toBeNull();
  },
);

test('缺少快照时各模块指明自身前置，知识卡片仍可读', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => response(reads(path))),
  );
  show(`?project=${project}&section=import`);
  await screen.findByLabelText('导入源码 ZIP');
  for (const label of [
    '源码阅读',
    'API 分析',
    '静态关系图',
    '候选影响',
    '练习与实验',
    '模型讲解',
  ] as const) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    const current = screen.getByRole('region', { name: `${label}页面` });
    expect(
      within(current).getByText(`${label}需要先导入或选择一个快照。`),
    ).toBeTruthy();
    expect(
      within(current).getByRole('button', { name: '前往项目导入' }),
    ).toBeTruthy();
  }
  fireEvent.click(screen.getByRole('button', { name: '知识与学习' }));
  expectModule('知识与学习');
  expect(screen.getByRole('region', { name: '知识卡片' })).toBeTruthy();
  expect(screen.queryByRole('region', { name: '固定练习' })).toBeNull();
});

test('快照未选分析时各功能明确引导 API 分析而不共享主体', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => response(reads(path))),
  );
  show(`?project=${project}&snapshot=${snapshot}&section=api`);
  await screen.findByRole('combobox', { name: '根路由文件' });
  expect(
    screen.getByText('接口详情需要先在 API 分析中选择或提交分析。'),
  ).toBeTruthy();
  for (const label of [
    '静态关系图',
    '候选影响',
    '练习与实验',
    '模型讲解',
  ] as const) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    const current = screen.getByRole('region', { name: `${label}页面` });
    expect(
      within(current).getByText(`${label}需要先在 API 分析中选择或提交分析。`),
    ).toBeTruthy();
    expect(
      within(current).getByRole('button', { name: '前往 API 分析' }),
    ).toBeTruthy();
    expect(screen.queryByRole('combobox', { name: '根路由文件' })).toBeNull();
  }
});

test('已选分析未选接口时讲解与练习分别引导，图和 API 保持独立', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => response(reads(path))),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&section=api`,
  );
  await within(
    await screen.findByRole('navigation', { name: '接口导航' }),
  ).findByRole('button', { name: /POST/ });
  expect(screen.getByRole('region', { name: 'API 分析详情' })).toBeTruthy();
  expect(screen.queryByRole('region', { name: '静态关系图' })).toBeNull();
  for (const label of ['练习与实验', '模型讲解'] as const) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    expect(
      screen.getByText(`${label}需要先在 API 分析中选择一个接口。`),
    ).toBeTruthy();
  }
  fireEvent.click(screen.getByRole('button', { name: '静态关系图' }));
  expectModule('静态关系图');
  expect(screen.getByRole('region', { name: '静态关系图' })).toBeTruthy();
  expect(screen.queryByRole('region', { name: 'API 分析详情' })).toBeNull();
});

test('真实练习草稿跨 12 页与双主题保留，知识内容与作答独立且不自动提交', async () => {
  vi.stubGlobal('crypto', webcrypto);
  const exercise = {
    id: '00000000-0000-0000-0000-000000000009',
    slug: 'source-location',
    version: '1',
    answer_version: '1',
    example_version: 'task-board/1.0.0',
    kind: 'code_location',
    question: '定位请求校验的关键代码',
    hint: '核对源码行号',
    options: [{ id: 'root_urls.py', label: '根路由源码' }],
    review_note: '合成固定题，使用真实作答组件。',
    applicable: true,
    applicability_reason: '合成测试工作区匹配。',
  };
  const card = {
    id: '00000000-0000-0000-0000-000000000010',
    slug: 'request-validation',
    version: '1',
    title: '请求校验知识卡片',
    body: '只在知识页面阅读的正文',
    applicability: '任务教学',
    review_note: '合成知识内容',
  };
  const posts: string[] = [];
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (options.method === 'POST') posts.push(path);
    if (path.startsWith('/api/v1/exercises/?'))
      return response(page([exercise]));
    if (path.startsWith('/api/v1/knowledge-cards/?'))
      return response(page([card]));
    return response(reads(path));
  });
  vi.stubGlobal('fetch', fetcher);
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=labs`,
  );
  await screen.findByRole('spinbutton', { name: '起始行' });
  fireEvent.change(screen.getByRole('spinbutton', { name: '起始行' }), {
    target: { value: '8' },
  });
  fireEvent.change(screen.getByRole('spinbutton', { name: '结束行' }), {
    target: { value: '14' },
  });
  for (const [, label] of navigation) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    if (label !== '练习与实验') {
      expect(screen.queryByRole('region', { name: '固定练习' })).toBeNull();
      expect(screen.queryByRole('spinbutton', { name: '起始行' })).toBeNull();
    }
    if (label === '知识与学习') {
      const library = screen.getByRole('region', { name: '知识卡片' });
      expect(within(library).getByText(card.body)).toBeTruthy();
      expect(screen.queryByRole('button', { name: '提交作答' })).toBeNull();
    } else {
      expect(screen.queryByRole('region', { name: '知识卡片' })).toBeNull();
    }
  }
  fireEvent.click(screen.getByRole('button', { name: '练习与实验' }));
  expect(
    (screen.getByRole('spinbutton', { name: '起始行' }) as HTMLInputElement)
      .value,
  ).toBe('8');
  expect(
    (screen.getByRole('spinbutton', { name: '结束行' }) as HTMLInputElement)
      .value,
  ).toBe('14');
  fireEvent.click(screen.getByRole('button', { name: '切换为浅色模式' }));
  expect(document.documentElement.dataset.theme).toBe('light');
  expect(
    (screen.getByRole('spinbutton', { name: '起始行' }) as HTMLInputElement)
      .value,
  ).toBe('8');
  fireEvent.click(screen.getByRole('button', { name: '切换为深色模式' }));
  expect(document.documentElement.dataset.theme).toBe('dark');
  expect(
    (screen.getByRole('spinbutton', { name: '结束行' }) as HTMLInputElement)
      .value,
  ).toBe('14');
  expect(
    screen.getAllByRole('region', { name: '固定练习', hidden: true }),
  ).toHaveLength(1);
  expect(posts).toEqual([]);
});

test('项目名称与根路由草稿跨模块和主题保留，不触发创建或分析', async () => {
  const posts: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (options.method === 'POST') posts.push(path);
      return response(reads(path));
    }),
  );
  show(`?project=${project}&snapshot=${snapshot}&section=import`);
  await screen.findByLabelText('导入源码 ZIP');
  fireEvent.change(screen.getByRole('textbox', { name: '项目名称' }), {
    target: { value: '尚未提交的新项目' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'API 分析' }));
  fireEvent.change(
    await screen.findByRole('combobox', { name: '根路由文件' }),
    { target: { value: 'root_urls.py' } },
  );
  fireEvent.click(screen.getByRole('button', { name: '系统状态' }));
  fireEvent.click(screen.getByRole('button', { name: '切换为浅色模式' }));
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  expect(
    (screen.getByRole('textbox', { name: '项目名称' }) as HTMLInputElement)
      .value,
  ).toBe('尚未提交的新项目');
  fireEvent.click(screen.getByRole('button', { name: 'API 分析' }));
  expect(
    (screen.getByRole('combobox', { name: '根路由文件' }) as HTMLSelectElement)
      .value,
  ).toBe('root_urls.py');
  expect(posts).toEqual([]);
});

test('项目存在但快照失效时各模块引导重新导入，不查询下游或自动提交', async () => {
  const posts: string[] = [];
  const fetcher = vi.fn(async (path: string, options: RequestInit) => {
    if (options.method === 'POST') posts.push(path);
    if (path === `/api/v1/snapshots/${snapshot}/`)
      return new Response(
        JSON.stringify({
          code: 'NOT_FOUND',
          message: '所选快照不存在。',
          request_id: 'synthetic-missing-snapshot',
          details: {},
        }),
        { status: 404 },
      );
    return response(reads(path));
  });
  vi.stubGlobal('fetch', fetcher);
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=source`,
  );
  await within(screen.getByRole('region', { name: '源码阅读页面' })).findByText(
    '源码阅读所需的项目、快照或文件无法读取，请重新选择或重试。',
  );
  expect(screen.getByRole('alert').textContent).toContain('所选快照不存在。');
  for (const label of [
    '源码阅读',
    'API 分析',
    '静态关系图',
    '候选影响',
    '练习与实验',
    '模型讲解',
  ] as const) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    const current = screen.getByRole('region', { name: `${label}页面` });
    expect(
      within(current).getByText(
        `${label}所需的项目、快照或文件无法读取，请重新选择或重试。`,
      ),
    ).toBeTruthy();
    expect(
      within(current).getByRole('button', { name: '前往项目导入' }),
    ).toBeTruthy();
    expect(
      within(current).queryByRole('button', { name: '前往 API 分析' }),
    ).toBeNull();
  }
  expect(
    fetcher.mock.calls.some(
      ([path]) =>
        path.includes(`/snapshots/${snapshot}/files/`) ||
        path.includes(`/analyses/${analysis}/`),
    ),
  ).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: '前往项目导入' }));
  expectModule('项目导入');
  expect(screen.getByLabelText('导入源码 ZIP')).toBeTruthy();
  expect(readSelection(window.location.search).project).toBe(project);
  expect(posts).toEqual([]);
});

test('快照读取中各模块显示自身加载状态，完成后恢复内容且不误导选择接口', async () => {
  let finish!: (value: Response) => void;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string) => {
      if (path === `/api/v1/snapshots/${snapshot}/`)
        return new Promise<Response>((resolve) => {
          finish = resolve;
        });
      return response(reads(path));
    }),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=source`,
  );
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  for (const label of [
    '源码阅读',
    'API 分析',
    '静态关系图',
    '候选影响',
    '练习与实验',
    '模型讲解',
  ] as const) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    const current = screen.getByRole('region', { name: `${label}页面` });
    expect(within(current).getByRole('status').textContent).toBe(
      `${label}：正在读取所需的项目与快照…`,
    );
    expect(within(current).queryByText(/需要先在 API 分析中选择/)).toBeNull();
    expect(
      within(current).queryByRole('button', { name: '前往 API 分析' }),
    ).toBeNull();
    expect(
      within(current).queryByRole('button', { name: '前往项目导入' }),
    ).toBeNull();
  }
  await act(async () => {
    finish(response(snapshotDto));
  });
  await screen.findByRole('region', { name: '源码讲解' });
  expectModule('模型讲解');
  expect(screen.queryByText('模型讲解：正在读取所需的项目与快照…')).toBeNull();
});

test('删除侧栏装饰和全局项目横幅后，各页面保留导航与工作台摘要', async () => {
  const posts: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (options.method === 'POST') posts.push(path);
      return response(reads(path));
    }),
  );
  show(`?project=${project}&snapshot=${snapshot}&section=import`);
  await screen.findByLabelText('导入源码 ZIP');
  const sidebar = within(
    screen.getByRole('navigation', { name: '功能导航' }).closest('aside')!,
  );
  expect(sidebar.getAllByRole('button')).toHaveLength(navigation.length);
  expect(sidebar.queryByText(/从源码证据出发/)).toBeNull();
  expect(sidebar.queryByText('本地学习工作台')).toBeNull();
  for (const [, label] of navigation) {
    fireEvent.click(sidebar.getByRole('button', { name: label }));
    expectModule(label);
    expect(screen.queryByRole('button', { name: '打开项目' })).toBeNull();
    if (label === '工作台') {
      expect(
        await within(
          screen.getByRole('region', { name: '工作台页面' }),
        ).findByRole('heading', { name: projectDto.name, level: 2 }),
      ).toBeTruthy();
      expect(screen.getByText('已接收源码')).toBeTruthy();
    } else {
      expect(
        screen.queryByRole('heading', { name: projectDto.name }),
      ).toBeNull();
    }
  }
  expect(readSelection(window.location.search).project).toBe(project);
  expect(readSelection(window.location.search).snapshot).toBe(snapshot);
  expect(posts).toEqual([]);
});

test('点击品牌返回工作台保留项目快照和未提交表单，不重新加载或写入', async () => {
  const writes: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (options.method === 'POST') writes.push(path);
      return response(reads(path));
    }),
  );
  show(`?project=${project}&snapshot=${snapshot}&section=import`);
  await screen.findByLabelText('导入源码 ZIP');
  fireEvent.change(screen.getByRole('textbox', { name: '项目名称' }), {
    target: { value: '尚未提交的草稿' },
  });
  fireEvent.click(screen.getByRole('link', { name: '项目解读实验室首页' }));
  expectModule('工作台');
  expect(readSelection(window.location.search)).toMatchObject({
    project,
    snapshot,
    section: 'workbench',
  });
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  expect(screen.getByRole('textbox', { name: '项目名称' })).toHaveProperty(
    'value',
    '尚未提交的草稿',
  );
  expect(writes).toEqual([]);
});

test('快照命名草稿仅在导入和对比页可见，跨 12 页与双主题保留且不自动写入', async () => {
  const writes: string[] = [];
  const savedName = '任务簿创建任务基线';
  vi.stubGlobal(
    'fetch',
    vi.fn(async (path: string, options: RequestInit) => {
      if (options.method === 'POST' || options.method === 'PATCH')
        writes.push(`${options.method} ${path}`);
      if (path === `/api/v1/snapshots/${snapshot}/`)
        return response({ ...snapshotDto, name: savedName });
      if (
        new URL(path, 'http://local.test').pathname ===
        `/api/v1/projects/${project}/snapshots/`
      )
        return response(page([{ ...snapshotDto, name: savedName }]));
      return response(reads(path));
    }),
  );
  show(
    `?project=${project}&snapshot=${snapshot}&analysis=${analysis}&endpoint=0&section=import&file=root_urls.py&start=1&end=1&file2=root_urls.py&start2=1&end2=1`,
  );
  await screen.findByText('命名当前快照');
  fireEvent.click(screen.getByRole('button', { name: '命名当前快照' }));
  fireEvent.change(await screen.findByRole('textbox', { name: '快照名称' }), {
    target: { value: '尚未保存的任务簿快照' },
  });
  for (const [, label] of navigation) {
    fireEvent.click(screen.getByRole('button', { name: label }));
    expectModule(label);
    if (label === '源码阅读') {
      for (const name of ['只读源码', '固定只读源码']) {
        const viewer = within(screen.getByRole('region', { name }));
        expect(await viewer.findByText(new RegExp(savedName))).toBeTruthy();
        expect(viewer.queryByText(new RegExp(snapshot.slice(0, 8)))).toBeNull();
        expect(viewer.queryByText(/尚未保存的任务簿快照/)).toBeNull();
      }
    }
    if (label === '项目导入' || label === '快照与对比') {
      expect(
        (screen.getByRole('textbox', { name: '快照名称' }) as HTMLInputElement)
          .value,
      ).toBe('尚未保存的任务簿快照');
      expect(screen.getByRole('form', { name: '快照命名' })).toBeTruthy();
    } else {
      expect(screen.queryByRole('textbox', { name: '快照名称' })).toBeNull();
      expect(screen.queryByRole('form', { name: '快照命名' })).toBeNull();
    }
  }
  fireEvent.click(screen.getByRole('button', { name: '快照与对比' }));
  fireEvent.click(screen.getByRole('button', { name: '切换为浅色模式' }));
  expect(document.documentElement.dataset.theme).toBe('light');
  expect(
    (screen.getByRole('textbox', { name: '快照名称' }) as HTMLInputElement)
      .value,
  ).toBe('尚未保存的任务簿快照');
  fireEvent.click(screen.getByRole('button', { name: '项目导入' }));
  fireEvent.click(screen.getByRole('button', { name: '切换为深色模式' }));
  expect(document.documentElement.dataset.theme).toBe('dark');
  expect(
    (screen.getByRole('textbox', { name: '快照名称' }) as HTMLInputElement)
      .value,
  ).toBe('尚未保存的任务簿快照');
  expect(
    screen.getAllByRole('form', { name: '快照命名', hidden: true }),
  ).toHaveLength(1);
  expect(writes).toEqual([]);
});
