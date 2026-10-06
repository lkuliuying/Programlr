import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type {
  ContextPreview,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { getJob } from '../jobs';
import * as api from './api/explanations-api';

function readConsent(key: string): string | null {
  try {
    const value = sessionStorage.getItem(key);
    return value && /^[0-9a-f-]{36}$/.test(value) ? value : null;
  } catch {
    return null;
  }
}

type Props = {
  selected: api.Selection;
  previewId: string | null;
  explanationId: string | null;
  jobId: string | null;
  onSelect: (selection: {
    preview?: string | null;
    explanation?: string | null;
    job?: string | null;
  }) => void;
  onSource: (ref: SourceRef) => void;
};
function ExplanationSteps({ step }: { step: number }) {
  return (
    <ol className="explanation-steps" aria-label="讲解步骤">
      {['准备外发预览', '审阅并保存本次确认', '提交生成与读取结果'].map(
        (label, index) => (
          <li
            key={label}
            aria-current={step === index + 1 ? 'step' : undefined}
          >
            {label}
          </li>
        ),
      )}
    </ol>
  );
}
export function ExplanationPanel(props: Props) {
  const { selected, previewId, explanationId, jobId, onSelect, onSource } =
    props;
  const [historyPage, setHistoryPage] = useState(1);
  const history = useQuery({
    queryKey: ['explanations', 'history', selected, historyPage, explanationId],
    queryFn: ({ signal }) =>
      api.explanationHistory(selected, historyPage, signal),
  });
  const preview = useQuery({
    queryKey: ['explanations', 'preview', selected, previewId],
    queryFn: ({ signal }) => api.getPreview(previewId!, selected, signal),
    enabled: !!previewId,
  });
  const explanation = useQuery({
    queryKey: ['explanations', 'detail', selected, explanationId],
    queryFn: ({ signal }) =>
      api.getExplanation(explanationId!, selected, signal),
    enabled: !!explanationId,
  });
  const operation = useIdempotentOperation<
    { nodes: string[] | null; excluded: string[] },
    ContextPreview
  >(
    `preview.${selected.analysis}.${selected.endpoint}`,
    JSON.stringify,
    (nodes, key, signal) => api.createPreview(selected, nodes, key, signal),
    (item) => onSelect({ preview: item.id, explanation: null, job: null }),
  );
  return (
    <section aria-label="源码讲解">
      <h3 className="explanation-heading">
        源码讲解
        <span className="model-badge">
          {preview.data?.configuration.model ??
            explanation.data?.model ??
            '未准备讲解'}
        </span>
      </h3>
      {!preview.data && <ExplanationSteps step={explanation.data ? 3 : 1} />}
      <p>先审阅完整外发消息，再确认并提交。预览、拒绝和刷新均不会调用模型。</p>
      <Button
        loading={operation.isPending}
        onClick={() => operation.start({ nodes: null, excluded: [] })}
      >
        准备外发预览
      </Button>
      <Feedback
        error={
          operation.error ?? preview.error ?? explanation.error ?? history.error
        }
      />
      {preview.isFetching && <p role="status">读取已保存预览…</p>}
      {preview.data && (
        <PreviewReview
          key={preview.data.id}
          preview={preview.data}
          jobId={jobId}
          onSelect={onSelect}
          onSource={onSource}
          regenerate={(nodes, excluded) => operation.start({ nodes, excluded })}
        />
      )}
      {explanation.data && (
        <article className="explanation-result">
          <h4>讲解结果</h4>
          <p>
            模型：{explanation.data.model} · 模板{' '}
            {explanation.data.template_version} ·{' '}
            {new Date(explanation.data.created_at).toLocaleString('zh-CN')}
          </p>
          <p>
            用量：
            {explanation.data.usage
              ? `输入 ${explanation.data.usage.prompt_tokens} / 输出 ${explanation.data.usage.completion_tokens} / 合计 ${explanation.data.usage.total_tokens} token`
              : '未知（供应商未报告用量，实际费用请查看供应商账单）'}
          </p>
          <p role="note">
            引用位置核验不等于结论正确。请结合源码和静态分析限制复核。
          </p>
          {(
            [
              ['purpose', '做什么'],
              ['evidence', '依据'],
              ['mechanism', '工作原理'],
              ['knowledge', '相关知识'],
              ['verification', '如何验证'],
            ] as const
          ).map(([key, title]) => (
            <section key={key}>
              <h4>{title}</h4>
              {explanation.data!.content[key].map((claim, index) => (
                <div key={index}>
                  <small>
                    {
                      {
                        source_fact: '源码事实',
                        static_inference: '静态推断',
                        general_principle: '通用原理',
                      }[claim.kind]
                    }
                  </small>
                  <p>{claim.text}</p>
                  {claim.source_refs.map((ref, index) => (
                    <button
                      type="button"
                      className="source-link"
                      key={index}
                      onClick={() => onSource(ref)}
                    >
                      {ref.file_path}:{ref.start_line}–{ref.end_line}
                    </button>
                  ))}
                </div>
              ))}
            </section>
          ))}
        </article>
      )}
      <h4>讲解历史</h4>
      {history.isPending && <p role="status">读取历史…</p>}
      {history.data?.results.length === 0 && <p>该接口暂无有效讲解。</p>}
      {history.data?.results.map((item) => (
        <p key={item.id}>
          <button
            type="button"
            className="source-link"
            onClick={() =>
              onSelect({
                explanation: item.id,
                preview: item.preview_id,
                job: null,
              })
            }
          >
            {new Date(item.created_at).toLocaleString('zh-CN')} · {item.model}
          </button>
        </p>
      ))}
      <PageControls
        page={historyPage}
        previous={history.data?.previous ?? null}
        next={history.data?.next ?? null}
        onPage={setHistoryPage}
      />
    </section>
  );
}
function PreviewReview({
  preview,
  jobId,
  onSelect,
  onSource,
  regenerate,
}: {
  preview: ContextPreview;
  jobId: string | null;
  onSelect: Props['onSelect'];
  onSource: Props['onSource'];
  regenerate: (nodes: string[], excluded: string[]) => void;
}) {
  const [nodes, setNodes] = useState(preview.nodes.map((node) => node.id));
  const [accepted, setAccepted] = useState(false);
  const [excluded, setExcluded] = useState<string[]>(preview.excluded_snippets);
  const job = useQuery({
    queryKey: ['jobs', 'detail', jobId],
    queryFn: ({ signal }) => getJob(jobId!, signal),
    enabled: !!jobId,
    refetchInterval: (query) =>
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.status)
        ? 1500
        : false,
  });
  // 仅保存确认标识，刷新后仍需用户主动提交；正文与凭据不进入浏览器持久存储。
  const consentStorage = `learning-lab.consent.${preview.id}`;
  const [consent, setConsent] = useState<string | null>(() =>
    readConsent(consentStorage),
  );
  const confirmation = useIdempotentOperation<
    boolean,
    Awaited<ReturnType<typeof api.confirmPreview>>
  >(
    `consent.${preview.id}`,
    JSON.stringify,
    (_, key, signal) => api.confirmPreview(preview.id, key, signal),
    (item) => {
      sessionStorage.setItem(consentStorage, item.id);
      setConsent(item.id);
    },
  );
  const generation = useIdempotentOperation<
    string,
    Awaited<ReturnType<typeof api.generateExplanation>>
  >(
    `explanation.${preview.id}.${job.data?.status === 'failed' ? job.data.id : 'new'}`,
    (value) => value,
    (value, key, signal) =>
      api.generateExplanation(
        value,
        job.data?.status === 'failed' ? job.data.id : null,
        key,
        signal,
      ),
    (item) => {
      sessionStorage.removeItem(consentStorage);
      setConsent(null);
      setAccepted(false);
      onSelect({ job: item.id, explanation: null });
    },
    (id) => onSelect({ job: id }),
  );
  const selectedAll =
    nodes.length === preview.nodes.length &&
    excluded.length === preview.excluded_snippets.length &&
    excluded.every((id) => preview.excluded_snippets.includes(id));
  const jobValid =
    job.data?.kind === 'explanation' &&
    job.data.snapshot_id === preview.snapshot_id;
  const legacyPreview =
    preview.template_version !== '1.1.0' ||
    preview.configuration.timeout !== undefined ||
    preview.configuration.context_bytes !== undefined ||
    preview.configuration.output_tokens !== undefined ||
    preview.configuration.token_field !== undefined;
  return (
    <div className="context-preview">
      <ExplanationSteps step={consent ? 3 : 2} />
      <h4>待发送内容</h4>
      <dl>
        <dt>固定目标</dt>
        <dd>{preview.configuration.base_url}</dd>
        <dt>模型 / 模板</dt>
        <dd>
          {preview.configuration.model} / {preview.template_version}
        </dd>
        <dt>发送内容</dt>
        <dd>{preview.context_bytes} 字节</dd>
        {legacyPreview && (
          <>
            <dt>历史请求参数</dt>
            <dd>
              上下文 {preview.configuration.context_bytes} 字节；输出{' '}
              {preview.configuration.output_tokens} token；期限{' '}
              {preview.configuration.timeout} 秒；
              {preview.configuration.token_field}
            </dd>
          </>
        )}
      </dl>
      <p>
        {legacyPreview
          ? '这是保留原参数的历史预览，继续发送前请重新准备预览。'
          : '应用不设置 token、请求时长或消息大小上限；供应商仍可能有容量和超时限制，实际费用请自行查看供应商账单。'}
      </p>
      <p>
        快照 {preview.snapshot_id} · 接口 #{preview.endpoint_index} · 摘要{' '}
        {preview.payload_digest}
      </p>
      <p>
        遗漏或截断：{preview.omissions.join('、') || '无'}
        。静态关系不代表运行时必然发生。
      </p>
      {!!preview.knowledge_cards?.length && (
        <details>
          <summary>
            本次匹配的知识卡片（{preview.knowledge_cards.length}）
          </summary>
          {preview.knowledge_cards.map((card) => (
            <article key={card.card_id}>
              <h5>
                {card.title} · {card.version}
              </h5>
              <p>{card.body}</p>
              {card.source_refs.map((ref, index) => (
                <button key={index} onClick={() => onSource(ref)}>
                  {ref.file_path}:{ref.start_line}–{ref.end_line}
                </button>
              ))}
            </article>
          ))}
        </details>
      )}
      <fieldset>
        <legend>选择节点范围</legend>
        {preview.nodes.map((node) => (
          <label key={node.id}>
            <input
              type="checkbox"
              checked={nodes.includes(node.id)}
              onChange={(event) =>
                setNodes(
                  event.target.checked
                    ? [...nodes, node.id]
                    : nodes.filter((id) => id !== node.id),
                )
              }
            />
            {node.name}
          </label>
        ))}
        <Button
          disabled={selectedAll || !nodes.length}
          onClick={() =>
            regenerate(
              nodes,
              nodes.length === preview.nodes.length ? excluded : [],
            )
          }
        >
          按所选节点重新预览
        </Button>
      </fieldset>
      {preview.snippets.map((item, index) => (
        <details key={index}>
          <summary>
            {item.source_ref.file_path}:{item.source_ref.start_line}–
            {item.source_ref.end_line}
          </summary>
          <pre>{item.content}</pre>
          <label>
            <input
              type="checkbox"
              checked={excluded.includes(item.id)}
              onChange={(event) =>
                setExcluded(
                  event.target.checked
                    ? [...excluded, item.id]
                    : excluded.filter((id) => id !== item.id),
                )
              }
            />
            从新预览排除此片段
          </label>
          <button type="button" onClick={() => onSource(item.source_ref)}>
            定位源码
          </button>
        </details>
      ))}
      <details>
        <summary>审阅完整消息（含固定模板）</summary>
        {preview.messages.map((message, index) => (
          <section key={index}>
            <h5>{message.role}</h5>
            <pre>{message.content}</pre>
          </section>
        ))}
      </details>
      <label>
        <input
          type="checkbox"
          checked={accepted}
          onChange={(event) => setAccepted(event.target.checked)}
        />
        我已审阅以上范围，允许向所示模型发送一次；可能计费。
      </label>
      <div className="panel-actions" data-page-keep>
        <Button
          onClick={() => {
            sessionStorage.removeItem(consentStorage);
            onSelect({ preview: null });
          }}
        >
          拒绝外发
        </Button>
        <Button
          disabled={
            !accepted ||
            legacyPreview ||
            !selectedAll ||
            (!!job.data && ['queued', 'running'].includes(job.data.status))
          }
          loading={confirmation.isPending}
          onClick={() => confirmation.start(true)}
        >
          保存本次确认
        </Button>
        <Button
          disabled={legacyPreview || !consent || !selectedAll}
          loading={generation.isPending}
          onClick={() => consent && generation.start(consent)}
        >
          {jobValid && job.data?.status === 'failed'
            ? '重新确认后重试（可能重复计费）'
            : '提交本次讲解'}
        </Button>
      </div>
      <Feedback error={confirmation.error ?? generation.error ?? job.error} />
      {jobValid && (
        <div role="status">
          <p>讲解任务：{job.data!.status}</p>
          {job.data!.error && (
            <p>
              {job.data!.error.code}：{job.data!.error.message}
            </p>
          )}
          {job.data!.status === 'succeeded' && job.data!.result_url && (
            <Button
              onClick={() =>
                onSelect({ explanation: job.data!.result_url!.split('/')[4] })
              }
            >
              阅读本次讲解
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
