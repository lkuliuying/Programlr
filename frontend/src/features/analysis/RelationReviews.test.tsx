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
import { ApiError } from '../../shared/api/client';
import type {
  Graph,
  RelationReview,
  RelationReviewInputRequest,
  RelationReviewState,
} from '../../shared/api/generated/schema';
import { RelationReviews } from './RelationReviews';
import * as api from './api/review-api';
import { parseGraph } from './api/analysis-api';

vi.mock('./api/review-api', async (original) => ({
  ...(await original<typeof api>()),
  listReviews: vi.fn(),
  submitReview: vi.fn(),
}));
const uuid = (value: number) =>
  `00000000-0000-0000-0000-${String(value).padStart(12, '0')}`;
const analysis = uuid(1),
  snapshot = uuid(2),
  request = uuid(3),
  targets = [uuid(4), uuid(5)];
const reference = {
  snapshot_id: snapshot,
  file_path: 'views.py',
  start_line: 1,
  end_line: 1,
};
const proof = {
  kind: 'source_fact' as const,
  rule: 'fixture',
  source_ref: reference,
};
const graph: Graph = {
  analysis_id: analysis,
  snapshot_id: snapshot,
  graph_version: 'analysis-graph/2.0.0',
  rule_version: 'fixture',
  root_node_id: null,
  endpoint_index: null,
  algorithm: 'bfs',
  nodes: targets.map((target, index) => ({
    id: target,
    name: `GET /target-${index}/`,
    kind: 'endpoint',
    endpoint: {
      index,
      method: 'GET',
      path: `/target-${index}/`,
      path_kind: 'django_path',
      action: 'list',
      is_candidate: false,
    },
    request: null,
    source_ref: reference,
    evidence: [proof],
  })),
  edges: targets.map((target, index) => ({
    id: uuid(6 + index),
    source_id: request,
    target_id: target,
    relation: 'candidate_match',
    evidence: [proof],
  })),
  relation_reviews: targets.map((target) => ({
    request_id: request,
    target_id: target,
    revision: 0,
    decision: 'undecided',
  })),
  coverage: {
    python_files: 1,
    parsed_files: 1,
    syntax_failed_files: 0,
    skipped_files: 0,
    endpoint_count: 2,
    diagnostic_count: 0,
    complete: true,
    limitations: [],
  },
  diagnostics_url: `/api/v1/analyses/${analysis}/diagnostics/`,
  total_nodes: 3,
  total_edges: 2,
  returned_nodes: 3,
  returned_edges: 2,
  truncated: false,
  truncation_reasons: [],
};
graph.nodes.unshift({
  id: request,
  name: '请求',
  kind: 'frontend_request',
  endpoint: null,
  source_ref: reference,
  evidence: [proof],
  request: {
    method: 'GET',
    path: '/target/',
    original_path: '/target/',
    status: 'candidate',
    reason: 'multiple_endpoints',
  },
});
let state: RelationReviewState;
let records: RelationReview[];
const onSource = vi.fn();
function history() {
  return {
    count: records.length,
    next: null,
    previous: null,
    results: [...records],
    state: { ...state, excluded_target_ids: [...state.excluded_target_ids] },
  };
}
function apply(input: RelationReviewInputRequest) {
  if (input.action === 'confirm') {
    state.confirmed_target_id = input.target_id;
    state.excluded_target_ids = state.excluded_target_ids.filter(
      (id) => id !== input.target_id,
    );
  } else {
    if (state.confirmed_target_id === input.target_id)
      state.confirmed_target_id = null;
    state.excluded_target_ids = state.excluded_target_ids.filter(
      (id) => id !== input.target_id,
    );
    if (input.action === 'exclude')
      state.excluded_target_ids.push(input.target_id);
  }
  state.revision++;
  const record = {
    id: uuid(20 + state.revision),
    analysis_id: analysis,
    request_id: request,
    target_id: input.target_id,
    action: input.action,
    revision: state.revision,
    created_at: '2026-09-30T00:00:00Z',
  };
  records.unshift(record);
  return { record, state: history().state };
}
function show(analysisId = analysis, requestId = request) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    client,
    ...render(
      <QueryClientProvider client={client}>
        <RelationReviews
          snapshotId={snapshot}
          analysisId={analysisId}
          requestId={requestId}
          graph={graph}
          onSource={onSource}
        />
      </QueryClientProvider>,
    ),
  };
}
const targetPanel = (index: number) =>
  within(
    screen.getByRole('article', { name: `候选目标 GET /target-${index}/` }),
  );
beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.stubGlobal('crypto', webcrypto);
  state = {
    analysis_id: analysis,
    request_id: request,
    revision: 0,
    confirmed_target_id: null,
    excluded_target_ids: [],
  };
  records = [];
  vi.mocked(api.listReviews).mockImplementation(async () => history());
  vi.mocked(api.submitReview).mockImplementation(async (_analysis, input) =>
    apply(input),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test('确认、排除、撤销使用当前修订；历史与源码定位可读，其他候选保持未决', async () => {
  show();
  await screen.findByText('当前修订：0');
  const confirm = targetPanel(0).getByRole('button', { name: '确认关系' });
  confirm.focus();
  expect(document.activeElement).toBe(confirm);
  fireEvent.click(confirm);
  await screen.findByText('当前修订：1');
  expect(targetPanel(0).getByText('人工确认')).toBeTruthy();
  expect(targetPanel(1).getByText('未决候选')).toBeTruthy();
  fireEvent.click(targetPanel(0).getByRole('button', { name: '排除关系' }));
  await screen.findByText('当前修订：2');
  expect(targetPanel(0).getByText('人工排除')).toBeTruthy();
  fireEvent.click(targetPanel(0).getByRole('button', { name: '撤销决定' }));
  await screen.findByText('当前修订：3');
  expect(targetPanel(0).getByText('未决候选')).toBeTruthy();
  expect(screen.getByText('决定历史（3 条）')).toBeTruthy();
  expect(
    vi
      .mocked(api.submitReview)
      .mock.calls.map((call) => call[1].expected_revision),
  ).toEqual([0, 1, 2]);
  fireEvent.click(targetPanel(0).getByRole('button', { name: 'views.py:1' }));
  expect(onSource).toHaveBeenCalledWith(reference);
  expect(
    [...Array(sessionStorage.length)].map((_, index) =>
      sessionStorage.key(index),
    ),
  ).toEqual([]);
});

test('丢失成功响应后刷新保持原输入与幂等键，读取的新修订不会导致重复决定', async () => {
  let accepted: ReturnType<typeof apply>;
  vi.mocked(api.submitReview)
    .mockImplementationOnce(async (_analysis, input) => {
      accepted = apply(input);
      throw new ApiError('结果未知', 0);
    })
    .mockImplementationOnce(async () => accepted);
  const first = show();
  await screen.findByText('当前修订：0');
  fireEvent.click(targetPanel(0).getByRole('button', { name: '确认关系' }));
  await screen.findByText('结果未知');
  expect(
    (
      targetPanel(1).getByRole('button', {
        name: '确认关系',
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  first.unmount();
  first.client.clear();
  show();
  await screen.findByText('当前修订：1');
  expect(api.submitReview).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '恢复上次提交' }));
  await waitFor(() =>
    expect(screen.queryByRole('button', { name: '恢复上次提交' })).toBeNull(),
  );
  const calls = vi.mocked(api.submitReview).mock.calls;
  expect(calls[0][1]).toEqual(calls[1][1]);
  expect(calls[0][2]).toBe(calls[1][2]);
  expect(records).toHaveLength(1);
});

test('修订冲突释放被拒绝的操作，重新读取后由用户手动选择', async () => {
  vi.mocked(api.submitReview).mockImplementationOnce(
    async (_analysis, input) => {
      apply({ ...input, target_id: targets[1] });
      throw new ApiError(
        '修订冲突',
        409,
        undefined,
        'RELATION_REVISION_CONFLICT',
      );
    },
  );
  show();
  await screen.findByText('当前修订：0');
  fireEvent.click(targetPanel(0).getByRole('button', { name: '确认关系' }));
  await screen.findByText('当前修订：1');
  expect(screen.getByText('修订冲突')).toBeTruthy();
  expect(api.submitReview).toHaveBeenCalledTimes(1);
  fireEvent.click(targetPanel(0).getByRole('button', { name: '确认关系' }));
  await screen.findByText('当前修订：2');
  const calls = vi.mocked(api.submitReview).mock.calls;
  expect(calls[1][1].expected_revision).toBe(1);
  expect(calls[1][2]).not.toBe(calls[0][2]);
});

test('恢复数据损坏时不发送新操作，历史仍可读取', async () => {
  sessionStorage.setItem(
    `learning-lab.relation-input.${analysis}.${request}`,
    '{broken',
  );
  show();
  await screen.findByText('当前修订：0');
  expect(screen.getByRole('alert').textContent).toContain('无法读取');
  fireEvent.click(targetPanel(0).getByRole('button', { name: '确认关系' }));
  expect(api.submitReview).not.toHaveBeenCalled();
});

test('切换分析不会恢复其他分析的未知操作，迟到成功不修改当前归属', async () => {
  let finish!: (result: ReturnType<typeof apply>) => void;
  vi.mocked(api.submitReview).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const first = show();
  await screen.findByText('当前修订：0');
  fireEvent.click(targetPanel(0).getByRole('button', { name: '确认关系' }));
  await waitFor(() => expect(finish).toBeTypeOf('function'));
  first.unmount();
  first.client.clear();
  show(uuid(50), uuid(51));
  await screen.findByText('当前修订：0');
  expect(screen.queryByRole('button', { name: '恢复上次提交' })).toBeNull();
  finish(
    apply({
      request_id: request,
      target_id: targets[0],
      action: 'confirm',
      expected_revision: 0,
    }),
  );
  await waitFor(() => expect(screen.getByText('当前修订：0')).toBeTruthy());
  expect(vi.mocked(api.listReviews).mock.calls.at(-1)?.[0]).toBe(uuid(50));
});

test('运行时拒绝跨分析历史、冲突状态、错误重放及越界修订', () => {
  const input = {
    request_id: request,
    target_id: targets[0],
    action: 'confirm' as const,
    expected_revision: 0,
  };
  const result = apply(input);
  expect(api.parseReviewPage(history(), analysis, request).state.revision).toBe(
    1,
  );
  for (const value of [
    { ...history(), state: { ...state, analysis_id: uuid(50) } },
    { ...history(), state: { ...state, excluded_target_ids: [targets[0]] } },
    {
      ...history(),
      next: `/api/v1/analyses/${analysis}/relation-reviews/?page=2&page_size=10&request_id=${uuid(50)}`,
    },
    { ...history(), results: [{ ...result.record, request_id: uuid(50) }] },
    { ...history(), results: [result.record, result.record] },
  ])
    expect(() => api.parseReviewPage(value, analysis, request)).toThrow();
  expect(() =>
    api.parseReviewResult(result, analysis, {
      ...input,
      target_id: targets[1],
    }),
  ).toThrow();
  expect(() =>
    api.parseReviewInput({ ...input, expected_revision: 2147483647 }, request),
  ).toThrow();
});

test('图中决定必须对应原候选边，缺失或错指元数据不能伪装成有效响应', () => {
  expect(
    parseGraph(graph, snapshot, analysis, null).relation_reviews,
  ).toHaveLength(2);
  expect(() =>
    parseGraph({ ...graph, relation_reviews: [] }, snapshot, analysis, null),
  ).toThrow();
  expect(() =>
    parseGraph(
      {
        ...graph,
        relation_reviews: graph.relation_reviews.map((review) => ({
          ...review,
          target_id: uuid(50),
        })),
      },
      snapshot,
      analysis,
      null,
    ),
  ).toThrow();
});
