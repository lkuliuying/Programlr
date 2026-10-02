import { useQuery } from '@tanstack/react-query';
import type { GraphNode, SourceRef } from '../../shared/api/generated/schema';
import { Icon } from '../../shared/components/Icon';
import { Feedback } from '../../shared/components/Feedback';
import { getGraph } from './api/analysis-api';
import { getImpact } from './api/impact-api';
import { getComparison } from './api/comparison-api';
import { GraphDiagram } from './GraphDiagram';

type Selection = {
  snapshot: string;
  analysis: string;
  endpoint: number | null;
};
export function GraphPanel({
  selected,
  node,
  compact = false,
  onNode,
  onExpand,
}: {
  selected: Selection | null;
  node: string | null;
  compact?: boolean;
  onNode: (node: GraphNode) => void;
  onExpand?: () => void;
}) {
  const query = useQuery({
    queryKey: [
      'analysis',
      selected?.snapshot,
      selected?.analysis,
      'graph',
      selected?.endpoint,
    ],
    queryFn: ({ signal }) =>
      getGraph(
        selected!.snapshot,
        selected!.analysis,
        selected!.endpoint,
        signal,
      ),
    enabled: !!selected,
  });
  const selectedNode = query.data?.nodes.find((item) => item.id === node);
  const reasons: Record<string, string> = {
    unique_method_path: '方法与完整路径唯一匹配',
    multiple_endpoints: '存在多个后端目标',
    unknown_base: '基础地址未知',
    dynamic: '路径或配置为动态值',
    external: '外部地址，无法确认本地目标',
    unsupported: '超出当前规则',
    no_matching_endpoint: '没有匹配的后端接口',
  };
  return (
    <section
      className="surface graph-panel"
      aria-label={compact ? '静态关系总览' : '静态关系图'}
    >
      <div className="panel-title">
        <Icon name="graph" />
        <h2>静态关系图</h2>
        {onExpand && (
          <button className="text-button" onClick={onExpand}>
            查看完整关系
          </button>
        )}
      </div>
      <div className="panel-body">
        <p className="panel-subtitle">源码事实与静态推断 · 不代表运行轨迹</p>
        <Feedback
          error={query.error}
          retry={() => {
            void query.refetch();
          }}
        />
        {!selected ? (
          <p className="panel-empty">
            选择快照并显式提交分析，查看有依据的前后端关联。
          </p>
        ) : query.isPending ? (
          <p role="status">读取关系图…</p>
        ) : (
          query.data && (
            <>
              <GraphDiagram
                nodes={query.data.nodes}
                edges={query.data.edges}
                reviews={query.data.relation_reviews}
                selected={node}
                compact={compact}
                onNode={onNode}
              />
              {selectedNode?.request && (
                <p className="pending-note">
                  {selectedNode.request.status === 'confirmed'
                    ? '静态确认'
                    : selectedNode.request.status === 'candidate'
                      ? '候选，待确认'
                      : '未匹配'}{' '}
                  ·{' '}
                  {reasons[selectedNode.request.reason] ??
                    '当前规则未提供原因说明'}
                </p>
              )}
              {(!query.data.coverage.complete || query.data.truncated) && (
                <p className="pending-note">
                  {query.data.truncated ? '结果已截断；' : ''}
                  部分静态结果，请核对覆盖说明与诊断。
                </p>
              )}
            </>
          )
        )}
      </div>
    </section>
  );
}
export function ImpactPreview({
  snapshot,
  analysis,
  node,
  candidates,
  onSource,
  onExpand,
}: {
  snapshot: string;
  analysis: string | null;
  node: string | null;
  candidates: boolean;
  onSource: (ref: SourceRef) => void;
  onExpand: () => void;
}) {
  const query = useQuery({
    queryKey: ['impact', analysis, node, candidates],
    queryFn: ({ signal }) =>
      getImpact(snapshot, analysis!, node!, candidates, signal),
    enabled: !!analysis && !!node,
  });
  return (
    <section className="surface impact-preview" aria-label="候选影响总览">
      <div className="panel-title">
        <Icon name="impact" />
        <h2>静态候选影响</h2>
        <button className="text-button" onClick={onExpand}>
          查看依据
        </button>
      </div>
      <div className="panel-body">
        <p className="panel-subtitle">有界反向遍历 · 不保证完整运行影响</p>
        <Feedback error={query.error} />
        {!node || !analysis ? (
          <p className="panel-empty">
            在关系图或 API 分析中选择节点，查看相关入口与证据路径。
          </p>
        ) : query.isPending ? (
          <p role="status">读取候选影响…</p>
        ) : (
          query.data && (
            <>
              <GraphDiagram
                nodes={query.data.nodes}
                edges={query.data.edges}
                reviews={query.data.relation_reviews}
                selected={node}
                compact
                onNode={(item) => {
                  if (item.source_ref) onSource(item.source_ref);
                }}
              />
              {query.data.truncated && (
                <p className="pending-note">结果已截断，剩余范围未判断。</p>
              )}
              {!query.data.results.length && (
                <p>当前图和预算内未找到相关入口，不能说明没有影响。</p>
              )}
            </>
          )
        )}
      </div>
    </section>
  );
}
export function ComparisonSummary({
  project,
  comparison,
  onExpand,
}: {
  project: string;
  comparison: string | null;
  onExpand: () => void;
}) {
  const query = useQuery({
    queryKey: ['comparisons', 'detail', project, comparison],
    queryFn: ({ signal }) => getComparison(comparison!, project, signal),
    enabled: !!comparison,
  });
  return (
    <section className="comparison-summary">
      <div className="section-heading">
        <h3>快照对比摘要</h3>
        <button className="text-button" onClick={onExpand}>
          {comparison ? '查看代码差异' : '选择两侧快照'}
        </button>
      </div>
      <Feedback error={query.error} />
      {query.data ? (
        <>
          <p>
            <code>{query.data.base_snapshot_id.slice(0, 8)}</code> →{' '}
            <code>{query.data.target_snapshot_id.slice(0, 8)}</code>
          </p>
          <p>差异版本 {query.data.comparison_version}</p>
          {query.data.comparison_notes.map((note) => (
            <p key={note} className="pending-note">
              {note}
            </p>
          ))}
        </>
      ) : (
        <p className="muted">显式选择基准与目标，保留各自快照和源码证据。</p>
      )}
    </section>
  );
}
