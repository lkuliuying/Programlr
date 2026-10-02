import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Tag } from 'antd';
import type {
  Graph,
  RelationReviewInputRequest,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { listReviews, parseReviewInput, submitReview } from './api/review-api';

const actions = { confirm: '确认关系', exclude: '排除关系', reset: '撤销决定' };
const labels = {
  confirmed: '人工确认',
  excluded: '人工排除',
  undecided: '未决候选',
};

export function RelationReviews({
  snapshotId,
  analysisId,
  requestId,
  graph,
  onSource,
}: {
  snapshotId: string;
  analysisId: string;
  requestId: string;
  graph: Graph;
  onSource: (reference: SourceRef) => void;
}) {
  const storage = `learning-lab.relation-input.${analysisId}.${requestId}`;
  const [restored] = useState(() => {
    try {
      const raw = sessionStorage.getItem(storage);
      return {
        input: raw ? parseReviewInput(JSON.parse(raw), requestId) : null,
        error: null,
      };
    } catch {
      return {
        input: null,
        error: new Error('保存的候选操作无法读取，请先核对决定历史。'),
      };
    }
  });
  const [intent, setIntent] = useState<RelationReviewInputRequest | null>(
    restored.input,
  );
  const [localError, setLocalError] = useState<Error | null>(restored.error);
  const [page, setPage] = useState(1);
  const client = useQueryClient();
  const prefix = ['analysis', snapshotId, analysisId];
  const history = useQuery({
    queryKey: [...prefix, 'reviews', requestId, page],
    queryFn: ({ signal }) => listReviews(analysisId, requestId, page, signal),
  });
  const refresh = () => {
    void client.invalidateQueries({ queryKey: prefix });
    void client.invalidateQueries({ queryKey: ['impact'] });
  };
  const clearIntent = () => {
    sessionStorage.removeItem(storage);
    setIntent(null);
  };
  const operation = useIdempotentOperation(
    `relation.${analysisId}.${requestId}`,
    JSON.stringify,
    (input: RelationReviewInputRequest, key, signal) =>
      submitReview(analysisId, input, key, signal),
    () => {
      clearIntent();
      setPage(1);
      refresh();
    },
    undefined,
    (_error, retained) => {
      if (!retained) {
        clearIntent();
        refresh();
      }
    },
  );
  const state = history.data?.state;
  const targets = graph.edges
    .filter(
      (edge) =>
        edge.relation === 'candidate_match' && edge.source_id === requestId,
    )
    .map((edge) => graph.nodes.find((node) => node.id === edge.target_id)!);
  const blocked =
    operation.isPending ||
    operation.pending ||
    !!intent ||
    !!localError ||
    !state ||
    !!history.error;
  const start = (
    target: string,
    action: RelationReviewInputRequest['action'],
  ) => {
    if (blocked || !state) return;
    const input = {
      request_id: requestId,
      target_id: target,
      action,
      expected_revision: state.revision,
    };
    try {
      // 仅保存操作身份；刷新后用原修订和原幂等键恢复未知提交。
      sessionStorage.setItem(storage, JSON.stringify(input));
      setIntent(input);
      operation.start(input);
    } catch {
      setLocalError(new Error('无法保存恢复信息，尚未提交决定。'));
    }
  };
  const name = (target: string) =>
    graph.nodes.find((node) => node.id === target)?.name ?? target;
  return (
    <section aria-label="候选人工处理">
      <h3>候选人工处理</h3>
      <p className="muted">
        人工决定用于关系展示和影响分析。模型讲解仍使用原有静态证据。
      </p>
      <Feedback error={localError ?? operation.error} />
      <Feedback
        error={history.error}
        retry={() => {
          void history.refetch();
        }}
      />
      {history.isPending && <p role="status">加载人工决定…</p>}
      {(intent || operation.pending) && (
        <p role="status">有一次提交待确认，请恢复同一操作后再处理其他候选。</p>
      )}
      {intent && (
        <Button
          disabled={operation.isPending || !!localError}
          onClick={() => operation.start(intent)}
        >
          恢复上次提交
        </Button>
      )}
      {state && (
        <>
          <p>当前修订：{state.revision}</p>
          {state.confirmed_target_id &&
            !targets.some(
              (target) => target.id === state.confirmed_target_id,
            ) && (
              <p className="pending-note">
                已人工确认的目标不在当前图返回范围：
                {name(state.confirmed_target_id)}。
              </p>
            )}
          {!targets.length && (
            <p>当前返回范围没有可操作候选，请打开全图或结合截断说明核对。</p>
          )}
          {targets.map((target) => {
            const decision =
              state.confirmed_target_id === target.id
                ? 'confirmed'
                : state.excluded_target_ids.includes(target.id)
                  ? 'excluded'
                  : 'undecided';
            return (
              <article key={target.id} aria-label={`候选目标 ${target.name}`}>
                <p>
                  <strong>{target.name}</strong> <Tag>{labels[decision]}</Tag>
                </p>
                <small>候选标识：{target.id}</small>
                {target.source_ref && (
                  <button
                    className="source-link"
                    onClick={() => onSource(target.source_ref!)}
                  >
                    {target.source_ref.file_path}:{target.source_ref.start_line}
                  </button>
                )}
                <div className="workspace-actions">
                  <Button
                    disabled={blocked || decision === 'confirmed'}
                    onClick={() => start(target.id, 'confirm')}
                  >
                    确认关系
                  </Button>
                  <Button
                    disabled={blocked || decision === 'excluded'}
                    onClick={() => start(target.id, 'exclude')}
                  >
                    排除关系
                  </Button>
                  <Button
                    disabled={blocked || decision === 'undecided'}
                    onClick={() => start(target.id, 'reset')}
                  >
                    撤销决定
                  </Button>
                </div>
              </article>
            );
          })}
          <details>
            <summary>决定历史（{history.data!.count} 条）</summary>
            <ol>
              {history.data!.results.map((record) => (
                <li key={record.id}>
                  修订 {record.revision} · {actions[record.action]} ·{' '}
                  {name(record.target_id)} ·{' '}
                  {new Date(record.created_at).toLocaleString()}
                </li>
              ))}
            </ol>
            <PageControls page={page} {...history.data!} onPage={setPage} />
          </details>
        </>
      )}
    </section>
  );
}
