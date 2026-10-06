import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExplanationPanel } from './ExplanationPanel';
import * as api from './api/explanations-api';
import { ApiError } from '../../shared/api/client';
import type {
  ContextPreview,
  Explanation,
  Job,
} from '../../shared/api/generated/schema';
import { getJob } from '../jobs';

vi.mock('./api/explanations-api', async (original) => ({
  ...(await original<typeof api>()),
  getPreview: vi.fn(),
  explanationHistory: vi.fn(),
  confirmPreview: vi.fn(),
  generateExplanation: vi.fn(),
  getExplanation: vi.fn(),
}));
vi.mock('../jobs', async (original) => ({
  ...(await original<typeof import('../jobs')>()),
  getJob: vi.fn(),
}));
const id = '00000000-0000-0000-0000-000000000001';
const selected = { snapshot: id, analysis: id, endpoint: 0 };
const preview: ContextPreview = {
  id,
  analysis_id: id,
  snapshot_id: id,
  endpoint_index: 0,
  payload_digest: 'a'.repeat(64),
  created_at: '2026-09-29T00:00:00Z',
  template_version: '1.1.0',
  configuration: {
    base_url: 'https://model-test.invalid/v1',
    model: 'test-model',
  },
  context_bytes: 300,
  messages: [
    { role: 'system', content: '固定模板' },
    { role: 'user', content: '不可信源码' },
  ],
  snippets: [
    {
      id: 'b'.repeat(64),
      source_ref: {
        snapshot_id: id,
        file_path: 'views.py',
        start_line: 1,
        end_line: 2,
      },
      sha256: 'c'.repeat(64),
      content: '示例源码',
    },
  ],
  nodes: [{ id, name: '创建任务', kind: 'view' }],
  omissions: [],
  excluded_snippets: [],
};
const onSelect = vi.fn();
const wrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
};
beforeEach(() => {
  vi.stubGlobal('crypto', webcrypto);
  sessionStorage.clear();
  vi.clearAllMocks();
  vi.mocked(api.getPreview).mockResolvedValue(preview);
  vi.mocked(api.explanationHistory).mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function panel() {
  return render(
    <ExplanationPanel
      selected={selected}
      previewId={id}
      explanationId={null}
      jobId={null}
      onSelect={onSelect}
      onSource={vi.fn()}
    />,
    { wrapper: wrapper() },
  );
}

test('拒绝预览不确认、不调用模型，完整模板仍可审阅', async () => {
  panel();
  await screen.findByText('待发送内容');
  fireEvent.click(screen.getByText('审阅完整消息（含固定模板）'));
  expect(screen.getByText('固定模板')).toBeTruthy();
  fireEvent.click(screen.getByText('拒绝外发'));
  expect(onSelect).toHaveBeenCalledWith({ preview: null });
  expect(api.confirmPreview).not.toHaveBeenCalled();
  expect(api.generateExplanation).not.toHaveBeenCalled();
});
test('确认与生成是独立操作，双击不重复提交', async () => {
  vi.mocked(api.confirmPreview).mockResolvedValue({
    id,
    preview_id: id,
    created_at: preview.created_at,
  });
  vi.mocked(api.generateExplanation).mockResolvedValue({
    id,
    kind: 'explanation',
    snapshot_id: id,
  } as Job);
  panel();
  await screen.findByText('待发送内容');
  fireEvent.click(
    screen.getByLabelText(
      '我已审阅以上范围，允许向所示模型发送一次；可能计费。',
    ),
  );
  fireEvent.click(screen.getByText('保存本次确认'));
  await waitFor(() =>
    expect(sessionStorage.getItem(`learning-lab.consent.${id}`)).toBe(id),
  );
  expect(api.generateExplanation).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('提交本次讲解'));
  fireEvent.click(screen.getByText('提交本次讲解'));
  await waitFor(() => expect(api.generateExplanation).toHaveBeenCalledTimes(1));
  await waitFor(() =>
    expect(onSelect).toHaveBeenCalledWith({ job: id, explanation: null }),
  );
});
test('明确失效不会留下阻塞新确认的旧操作键', async () => {
  sessionStorage.setItem(`learning-lab.consent.${id}`, id);
  vi.mocked(api.generateExplanation).mockRejectedValue(
    new ApiError('确认已失效', 409, 'trace', 'CONSENT_STALE'),
  );
  panel();
  await screen.findByText('待发送内容');
  fireEvent.click(screen.getByText('提交本次讲解'));
  await screen.findByText('确认已失效');
  expect(
    sessionStorage.getItem(`learning-lab.operation.explanation.${id}.new`),
  ).toBeNull();
});
test('切换选择后迟到的预览不能覆盖新接口', async () => {
  let resolve!: (item: ContextPreview) => void;
  vi.mocked(api.getPreview).mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const view = panel();
  view.rerender(
    <ExplanationPanel
      selected={{ ...selected, endpoint: 1 }}
      previewId={null}
      explanationId={null}
      jobId={null}
      onSelect={onSelect}
      onSource={vi.fn()}
    />,
  );
  resolve(preview);
  await waitFor(() => expect(screen.queryByText('待发送内容')).toBeNull());
});
test('运行时拒绝跨快照讲解预览', () => {
  expect(() =>
    api.parsePreview(preview, {
      ...selected,
      snapshot: '00000000-0000-0000-0000-000000000002',
    }),
  ).toThrow();
});

test('新预览只显示目标和实际内容大小并说明供应商负责限额', async () => {
  panel();
  expect(await screen.findByText('300 字节')).toBeTruthy();
  expect(
    screen.getByText(/应用不设置 token、请求时长或消息大小上限/),
  ).toBeTruthy();
  expect(screen.queryByText('限额参数')).toBeNull();
  expect(api.confirmPreview).not.toHaveBeenCalled();
  expect(api.generateExplanation).not.toHaveBeenCalled();
});

test('历史预算预览可读取，旧确认不能继续提交', async () => {
  sessionStorage.setItem(`learning-lab.consent.${id}`, id);
  vi.mocked(api.getPreview).mockResolvedValue({
    ...preview,
    configuration: {
      ...preview.configuration,
      timeout: 60,
      context_bytes: 65536,
      output_tokens: 4096,
      token_field: 'max_tokens',
    },
  });
  panel();
  expect(await screen.findByText(/这是保留原参数的历史预览/)).toBeTruthy();
  expect(screen.getByText(/输出 4096 token/)).toBeTruthy();
  expect(screen.getByText('提交本次讲解').closest('button')).toHaveProperty(
    'disabled',
    true,
  );
  expect(api.confirmPreview).not.toHaveBeenCalled();
  expect(api.generateExplanation).not.toHaveBeenCalled();
});

test('运行时完整读取超过原字节预算的消息和片段', () => {
  const large = '源'.repeat(70000);
  const value = api.parsePreview(
    {
      ...preview,
      context_bytes: 210000,
      messages: [preview.messages[0], { role: 'user', content: large }],
      snippets: [{ ...preview.snippets[0], content: large }],
    },
    selected,
  );
  expect(value.context_bytes).toBe(210000);
  expect(value.messages[1].content).toBe(large);
  expect(value.snippets[0].content).toBe(large);
});

test.each([
  {
    usage: {
      prompt_tokens: 6464,
      completion_tokens: 4096,
      total_tokens: 10560,
    },
    expected: '用量：输入 6464 / 输出 4096 / 合计 10560 token',
  },
  {
    usage: null,
    expected: '用量：未知（供应商未报告用量，实际费用请查看供应商账单）',
  },
  {
    usage: {
      prompt_tokens: 6464,
      completion_tokens: 14623,
      total_tokens: 21087,
    },
    expected: '用量：输入 6464 / 输出 14623 / 合计 21087 token',
  },
])(
  '讲解用量显示已报告明细或未知原因：$expected',
  async ({ usage, expected }) => {
    const explanation: Explanation = {
      id,
      job_id: id,
      preview_id: id,
      analysis_id: id,
      snapshot_id: id,
      endpoint_index: 0,
      template_version: '1.1.0',
      model: 'test-model',
      created_at: preview.created_at,
      usage,
      content: {
        purpose: [],
        evidence: [],
        mechanism: [],
        knowledge: [],
        verification: [],
      },
    };
    vi.mocked(api.getExplanation).mockResolvedValue(explanation);
    render(
      <ExplanationPanel
        selected={selected}
        previewId={null}
        explanationId={id}
        jobId={null}
        onSelect={onSelect}
        onSource={vi.fn()}
      />,
      { wrapper: wrapper() },
    );
    expect(await screen.findByText(expected)).toBeTruthy();
    expect(api.generateExplanation).not.toHaveBeenCalled();
  },
);

test('历史超限任务仍显示原失败且不自动重发', async () => {
  vi.mocked(getJob).mockResolvedValue({
    id,
    kind: 'explanation',
    snapshot_id: id,
    status: 'failed',
    stage: 'failed',
    progress: null,
    previous_job_id: null,
    parent_job_id: null,
    source_kind: '',
    result_deleted_at: null,
    result_deleted: false,
    result_url: null,
    error: {
      code: 'MODEL_OUTPUT_BUDGET_EXCEEDED',
      message:
        '供应商报告的输出用量超过本次请求上限，结果未发布。不会自动重发；供应商可能已处理请求，再次尝试可能计费。',
      details: {},
      request_id: 'test-request',
    },
    created_at: preview.created_at,
    updated_at: preview.created_at,
  });
  render(
    <ExplanationPanel
      selected={selected}
      previewId={id}
      explanationId={null}
      jobId={id}
      onSelect={onSelect}
      onSource={vi.fn()}
    />,
    { wrapper: wrapper() },
  );
  expect(await screen.findByText(/MODEL_OUTPUT_BUDGET_EXCEEDED/)).toBeTruthy();
  expect(screen.getByText('讲解任务：failed')).toBeTruthy();
  expect(screen.queryByText('阅读本次讲解')).toBeNull();
  expect(
    screen.getByText('重新确认后重试（可能重复计费）').closest('button'),
  ).toHaveProperty('disabled', true);
  expect(api.confirmPreview).not.toHaveBeenCalled();
  expect(api.generateExplanation).not.toHaveBeenCalled();
});
