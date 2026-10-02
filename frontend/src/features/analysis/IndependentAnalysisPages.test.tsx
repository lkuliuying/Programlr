import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type {
  Analysis,
  Endpoint,
  Graph,
  Impact,
  RelationReviewState,
} from '../../shared/api/generated/schema';
import { ApiError } from '../../shared/api/client';
import { AnalysisBrowser } from './AnalysisBrowser';
import { StaticGraphPanel } from './StaticGraphPanel';
import { CandidateImpactPanel } from './CandidateImpactPanel';
import * as api from './api/analysis-api';
import * as impactApi from './api/impact-api';
import * as reviewApi from './api/review-api';

vi.mock('./api/analysis-api', async (original) => ({
  ...(await original<typeof api>()),
  getAnalysis: vi.fn(),
  listEndpoints: vi.fn(),
  listDiagnostics: vi.fn(),
  getGraph: vi.fn(),
}));
vi.mock('./api/impact-api', async (original) => ({
  ...(await original<typeof impactApi>()),
  getImpact: vi.fn(),
}));
vi.mock('./api/review-api', async (original) => ({
  ...(await original<typeof reviewApi>()),
  listReviews: vi.fn(),
  submitReview: vi.fn(),
}));

const id = (value: number) =>
  `00000000-0000-0000-0000-${String(value).padStart(12, '0')}`;
const snapshot = id(1),
  analysis = id(2),
  request = id(3),
  target = id(4);
const reference = {
  snapshot_id: snapshot,
  file_path: 'views.py',
  start_line: 10,
  end_line: 20,
};
const evidence = {
  kind: 'source_fact' as const,
  rule: 'fixture.route',
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
const analysisDto: Analysis = {
  id: analysis,
  job_id: id(5),
  snapshot_id: snapshot,
  root_urlconf: 'urls.py',
  rule_version: 'fixture',
  coverage,
  frontend: null,
  created_at: '2026-10-01T00:00:00Z',
};
const endpoint: Endpoint = {
  index: 0,
  method: 'POST',
  path: '/tasks/',
  path_kind: 'django_path',
  action: 'post',
  view: { name: 'TaskCreateView', source_ref: reference },
  serializer: { name: 'TaskSerializer', source_ref: reference },
  model: null,
  evidence: [evidence],
  frontend_available: true,
  frontend_links: [
    {
      request_id: request,
      method: 'POST',
      path: '/tasks/',
      status: 'candidate',
      reason: 'unknown_base',
      source_ref: reference,
      relation_review: {
        request_id: request,
        target_id: target,
        revision: 0,
        decision: 'undecided',
      },
    },
  ],
};
const graph: Graph = {
  analysis_id: analysis,
  snapshot_id: snapshot,
  graph_version: 'analysis-graph/2.0.0',
  rule_version: 'fixture',
  root_node_id: null,
  endpoint_index: null,
  algorithm: 'bfs',
  nodes: [
    {
      id: request,
      kind: 'frontend_request',
      name: '创建任务请求',
      source_ref: reference,
      evidence: [evidence],
      endpoint: null,
      request: {
        method: 'POST',
        original_path: '/tasks/',
        path: '/tasks/',
        status: 'candidate',
        reason: 'unknown_base',
      },
    },
    {
      id: target,
      kind: 'endpoint',
      name: 'POST /tasks/',
      source_ref: reference,
      evidence: [evidence],
      endpoint: {
        index: 0,
        method: 'POST',
        path: '/tasks/',
        path_kind: 'django_path',
        action: 'post',
        is_candidate: false,
      },
      request: null,
    },
  ],
  edges: [
    {
      id: id(6),
      source_id: request,
      target_id: target,
      relation: 'candidate_match',
      evidence: [evidence],
    },
  ],
  relation_reviews: [
    {
      request_id: request,
      target_id: target,
      revision: 0,
      decision: 'undecided',
    },
  ],
  coverage,
  diagnostics_url: `/api/v1/analyses/${analysis}/diagnostics/`,
  total_nodes: 2,
  total_edges: 1,
  returned_nodes: 2,
  returned_edges: 1,
  truncated: false,
  truncation_reasons: [],
};
const impact: Impact = {
  analysis_id: analysis,
  snapshot_id: snapshot,
  graph_version: graph.graph_version,
  rule_version: graph.rule_version,
  include_candidates: false,
  max_nodes: 200,
  max_edges: 400,
  starts: [request],
  nodes: graph.nodes,
  edges: graph.edges,
  relation_reviews: graph.relation_reviews,
  results: [],
  visited_nodes: 2,
  visited_edges: 1,
  truncated: false,
  truncation_reasons: [],
  unmapped_files: [],
  uncovered_files: [],
  limitations: ['静态范围不代表运行轨迹'],
  diagnostics: [],
  diagnostics_url: graph.diagnostics_url,
};
const reviewState: RelationReviewState = {
  analysis_id: analysis,
  request_id: request,
  revision: 0,
  confirmed_target_id: null,
  excluded_target_ids: [],
};
const onSource = vi.fn(),
  onNode = vi.fn(),
  onEndpoint = vi.fn(),
  onCandidates = vi.fn();
const apiProps = {
  snapshotId: snapshot,
  analysisId: analysis,
  endpoint: 0,
  nodeId: request,
  onSource,
  onNode,
  onEndpoint,
};
const graphProps = {
  selected: { snapshot, analysis, endpoint: null },
  node: request,
  onNode,
  onSource,
};
const impactProps = {
  snapshot,
  analysis,
  endpoint: null,
  node: request,
  candidates: false,
  onNode,
  onSource,
  onCandidates,
};
const page = <T,>(results: T[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
});
function show(content: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const wrap = (children: ReactNode) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const view = render(wrap(content));
  return {
    ...view,
    update: (children: ReactNode) => view.rerender(wrap(children)),
    client,
  };
}
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  vi.mocked(api.getAnalysis).mockResolvedValue(analysisDto);
  vi.mocked(api.listEndpoints).mockResolvedValue(page([endpoint]));
  vi.mocked(api.listDiagnostics).mockResolvedValue(page([]));
  vi.mocked(api.getGraph).mockResolvedValue(graph);
  vi.mocked(impactApi.getImpact).mockResolvedValue(impact);
  vi.mocked(reviewApi.listReviews).mockResolvedValue({
    ...page([]),
    state: reviewState,
  });
  vi.mocked(reviewApi.submitReview).mockRejectedValue(
    new ApiError('结果未知', 0),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('API 页面只展示真实定义和请求来源，不读取关系图或挂人工表单', async () => {
  show(<AnalysisBrowser {...apiProps} />);
  expect(await screen.findByText('TaskCreateView')).toBeTruthy();
  expect(screen.getByText('TaskSerializer')).toBeTruthy();
  expect(screen.getByText(/未决候选 · 修订 0/)).toBeTruthy();
  const sources = screen.getAllByRole('button', { name: 'views.py:10–20' });
  fireEvent.click(sources[0]);
  expect(onSource).toHaveBeenCalledWith(reference);
  fireEvent.click(
    within(screen.getByRole('navigation', { name: '接口导航' })).getByRole(
      'button',
      { name: /POST.*\/tasks\// },
    ),
  );
  expect(onEndpoint).toHaveBeenCalledWith(0);
  fireEvent.click(screen.getByRole('button', { name: '清除接口选择' }));
  expect(onEndpoint).toHaveBeenLastCalledWith(null);
  expect(api.getGraph).not.toHaveBeenCalled();
  expect(reviewApi.listReviews).not.toHaveBeenCalled();
  expect(screen.queryByRole('region', { name: '静态关系图' })).toBeNull();
  expect(screen.queryByRole('region', { name: '候选人工处理' })).toBeNull();
});

test('接口地址选中清单另一页时读取对应页定义，不错误显示其他接口', async () => {
  const selected = {
    ...endpoint,
    index: 20,
    path: '/other/',
    view: { name: 'OtherView', source_ref: reference },
  };
  vi.mocked(api.listEndpoints).mockImplementation(
    async (_snapshot, _analysis, currentPage) =>
      page(currentPage === 2 ? [selected] : [endpoint]),
  );
  show(<AnalysisBrowser {...apiProps} endpoint={20} />);
  expect(await screen.findByText('OtherView')).toBeTruthy();
  expect(screen.queryByText('TaskCreateView')).toBeNull();
  expect(api.listEndpoints).toHaveBeenCalledWith(
    snapshot,
    analysis,
    2,
    expect.any(AbortSignal),
  );
});

test('静态图在画布内展示节点与边依据、候选状态与截断，不再读取上下说明与诊断', async () => {
  vi.mocked(api.getGraph).mockResolvedValue({
    ...graph,
    truncated: true,
    truncation_reasons: ['max_nodes'],
    total_nodes: 100,
  });
  const onFullGraph = vi.fn();
  const { container } = show(
    <StaticGraphPanel {...graphProps} onFullGraph={onFullGraph} />,
  );
  const graphRegion = await screen.findByRole('region', { name: '静态关系图' });
  fireEvent.click(
    await within(graphRegion).findByRole('button', {
      name: /^创建任务请求/,
    }),
  );
  expect(onNode).toHaveBeenCalledWith(graph.nodes[0]);
  expect(onSource).not.toHaveBeenCalled();
  expect(screen.getByRole('alert').textContent).toContain('结果已截断');
  expect(screen.getByText(/基础地址未知/)).toBeTruthy();
  fireEvent.click(
    within(
      screen.getByRole('complementary', { name: '图内依据' }),
    ).getAllByRole('button', { name: 'views.py:10–20' })[0],
  );
  expect(onSource).toHaveBeenCalledWith(reference);
  fireEvent.click(
    within(graphRegion).getByRole('button', { name: /^关系 1：/ }),
  );
  expect(
    within(screen.getByRole('complementary', { name: '图内依据' })).getByRole(
      'heading',
      { name: /候选匹配 · 未决候选/ },
    ),
  ).toBeTruthy();
  expect(
    screen.getAllByRole('complementary', { name: '图内依据' }),
  ).toHaveLength(1);
  fireEvent.click(screen.getByRole('button', { name: '关闭图内依据' }));
  expect(screen.queryByRole('complementary', { name: '图内依据' })).toBeNull();
  fireEvent.click(
    within(graphRegion).getByRole('button', { name: '查看全图' }),
  );
  expect(onFullGraph).toHaveBeenCalledTimes(1);
  expect(api.getAnalysis).not.toHaveBeenCalled();
  expect(api.listDiagnostics).not.toHaveBeenCalled();
  expect(container.querySelector('.analysis-summary')).toBeNull();
  expect(container.querySelector('.graph-scope-note')).toBeNull();
  expect(container.querySelector('.graph-edge-list')).toBeNull();
  expect(screen.queryByRole('region', { name: '诊断与缺口' })).toBeNull();
  expect(screen.queryByRole('navigation', { name: '接口导航' })).toBeNull();
  expect(screen.queryByRole('button', { name: '确认关系' })).toBeNull();
  expect(reviewApi.listReviews).not.toHaveBeenCalled();
});

test('静态图未选择分析时显示模块引导，不发送资源读取', () => {
  show(<StaticGraphPanel {...graphProps} selected={null} />);
  expect(screen.getByText(/选择快照并显式提交分析/)).toBeTruthy();
  expect(api.getGraph).not.toHaveBeenCalled();
  expect(api.getAnalysis).not.toHaveBeenCalled();
  expect(api.listDiagnostics).not.toHaveBeenCalled();
});

test('候选影响起点可独立选择，空起点不发影响查询', async () => {
  show(<CandidateImpactPanel {...impactProps} node={null} />);
  const picker = await screen.findByRole('combobox', { name: '选择图节点' });
  fireEvent.change(picker, { target: { value: request } });
  expect(onNode).toHaveBeenCalledWith(graph.nodes[0]);
  expect(impactApi.getImpact).not.toHaveBeenCalled();
  expect(reviewApi.submitReview).not.toHaveBeenCalled();
});

test('人工决定仅存在一个实例，切换模块不重发未知提交并保留原恢复键', async () => {
  const content = (visible: boolean) => (
    <>
      <div hidden={visible}>
        <AnalysisBrowser {...apiProps} />
        <StaticGraphPanel {...graphProps} />
      </div>
      <div hidden={!visible}>
        <CandidateImpactPanel {...impactProps} />
      </div>
    </>
  );
  const view = show(content(true));
  const review = await screen.findByRole('region', { name: '候选人工处理' });
  await within(review).findByText('当前修订：0');
  expect(
    screen.getAllByRole('region', { name: '候选人工处理', hidden: true }),
  ).toHaveLength(1);
  fireEvent.click(within(review).getByRole('button', { name: '确认关系' }));
  await screen.findByText('结果未知');
  expect(reviewApi.submitReview).toHaveBeenCalledTimes(1);
  const key = vi.mocked(reviewApi.submitReview).mock.calls[0][2];
  view.update(content(false));
  view.update(content(true));
  expect(
    await screen.findByRole('button', { name: '恢复上次提交' }),
  ).toBeTruthy();
  expect(reviewApi.submitReview).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '恢复上次提交' }));
  await waitFor(() => expect(reviewApi.submitReview).toHaveBeenCalledTimes(2));
  expect(vi.mocked(reviewApi.submitReview).mock.calls[1][2]).toBe(key);
  expect(vi.mocked(reviewApi.submitReview).mock.calls[1][1]).toEqual(
    vi.mocked(reviewApi.submitReview).mock.calls[0][1],
  );
});

test('全图截断遗漏已选起点仍读取精确影响，明确指出未返回范围', async () => {
  vi.mocked(api.getGraph).mockResolvedValue({
    ...graph,
    nodes: [],
    edges: [],
    relation_reviews: [],
    returned_nodes: 0,
    returned_edges: 0,
    truncated: true,
    truncation_reasons: ['max_nodes'],
  });
  show(<CandidateImpactPanel {...impactProps} />);
  expect(await screen.findByText(/所选节点不在全图返回范围/)).toBeTruthy();
  await waitFor(() =>
    expect(impactApi.getImpact).toHaveBeenCalledWith(
      snapshot,
      analysis,
      request,
      false,
      expect.any(AbortSignal),
    ),
  );
  expect(screen.queryByRole('button', { name: '确认关系' })).toBeNull();
  expect(api.getGraph).toHaveBeenCalledTimes(1);
  expect(api.getGraph).toHaveBeenCalledWith(
    snapshot,
    analysis,
    null,
    expect.any(AbortSignal),
  );
});

test('全图遗漏候选时回退当前接口范围，刷新后仍手动恢复同一人工提交', async () => {
  vi.mocked(api.getGraph).mockImplementation(
    async (_snapshot, _analysis, scope) =>
      scope === null
        ? {
            ...graph,
            nodes: [],
            edges: [],
            relation_reviews: [],
            returned_nodes: 0,
            returned_edges: 0,
            truncated: true,
            truncation_reasons: ['max_nodes'],
          }
        : { ...graph, endpoint_index: scope },
  );
  const first = show(<CandidateImpactPanel {...impactProps} endpoint={0} />);
  const review = await screen.findByRole('region', { name: '候选人工处理' });
  await within(review).findByText('当前修订：0');
  expect(screen.getByRole('alert').textContent).toContain('结果已截断');
  expect(screen.getByRole('combobox', { name: '选择图节点' })).toHaveProperty(
    'value',
    request,
  );
  expect(
    screen.getAllByRole('region', { name: '候选人工处理', hidden: true }),
  ).toHaveLength(1);
  expect(api.getGraph).toHaveBeenCalledWith(
    snapshot,
    analysis,
    0,
    expect.any(AbortSignal),
  );
  fireEvent.click(within(review).getByRole('button', { name: '确认关系' }));
  await screen.findByText('结果未知');
  const original = vi.mocked(reviewApi.submitReview).mock.calls[0];
  first.unmount();
  first.client.clear();
  show(<CandidateImpactPanel {...impactProps} endpoint={0} />);
  const restore = await screen.findByRole('button', { name: '恢复上次提交' });
  expect(reviewApi.submitReview).toHaveBeenCalledTimes(1);
  fireEvent.click(restore);
  await waitFor(() => expect(reviewApi.submitReview).toHaveBeenCalledTimes(2));
  const replay = vi.mocked(reviewApi.submitReview).mock.calls[1];
  expect(replay[1]).toEqual(original[1]);
  expect(replay[2]).toBe(original[2]);
});

test('全图已包含所选候选时不额外读取接口范围', async () => {
  show(<CandidateImpactPanel {...impactProps} endpoint={0} />);
  await screen.findByRole('region', { name: '候选人工处理' });
  expect(api.getGraph).toHaveBeenCalledTimes(1);
  expect(api.getGraph).toHaveBeenCalledWith(
    snapshot,
    analysis,
    null,
    expect.any(AbortSignal),
  );
});
