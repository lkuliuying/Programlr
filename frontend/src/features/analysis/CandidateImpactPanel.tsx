import { useQuery } from '@tanstack/react-query';
import type { GraphNode, SourceRef } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { getGraph } from './api/analysis-api';
import {
  EvidenceList,
  GraphScopeNote,
  ReferenceButton,
  nodeKinds,
} from './AnalysisEvidence';
import { NodeImpact } from './ImpactPanel';
import { RelationReviews } from './RelationReviews';

export function CandidateImpactPanel({
  snapshot,
  analysis,
  endpoint,
  node,
  candidates,
  onNode,
  onCandidates,
  onSource,
}: {
  snapshot: string;
  analysis: string;
  endpoint: number | null;
  node: string | null;
  candidates: boolean;
  onNode: (node: GraphNode) => void;
  onCandidates: (value: boolean) => void;
  onSource: (reference: SourceRef) => void;
}) {
  const graph = useQuery({
    queryKey: ['analysis', snapshot, analysis, 'graph', null],
    queryFn: ({ signal }) => getGraph(snapshot, analysis, null, signal),
  });
  const fullGraphNode = graph.data?.nodes.find((item) => item.id === node);
  const needsScopedGraph =
    !!graph.data && !!node && !fullGraphNode && endpoint !== null;
  const scopedGraph = useQuery({
    queryKey: ['analysis', snapshot, analysis, 'graph', endpoint],
    queryFn: ({ signal }) => getGraph(snapshot, analysis, endpoint, signal),
    enabled: needsScopedGraph,
  });
  const current =
    fullGraphNode ??
    (needsScopedGraph
      ? scopedGraph.data?.nodes.find((item) => item.id === node)
      : undefined);
  const reviewGraph = fullGraphNode ? graph.data : scopedGraph.data;
  return (
    <section aria-label="候选影响工作区">
      <p className="panel-subtitle">
        选择影响起点，核对有界反向遍历的相关入口与依据路径；人工决定仅修改展示和影响范围。
      </p>
      <Feedback
        error={graph.error}
        retry={() => {
          void graph.refetch();
        }}
      />
      {graph.isPending && <p role="status">读取影响起点与候选关系…</p>}
      {graph.data && (
        <>
          <GraphScopeNote graph={graph.data} />
          {needsScopedGraph && (
            <>
              <p className="pending-note">
                所选起点未在全图返回范围内，正在使用当前接口的有界关系核对候选；全图未返回范围仍待判断。
              </p>
              <Feedback
                error={scopedGraph.error}
                retry={() => {
                  void scopedGraph.refetch();
                }}
              />
              {scopedGraph.isPending && (
                <p role="status">读取当前接口范围的所选候选…</p>
              )}
              {scopedGraph.data && <GraphScopeNote graph={scopedGraph.data} />}
            </>
          )}
          <div className="candidate-impact-columns">
            <nav className="surface endpoint-nav" aria-label="影响起点选择">
              <div className="panel-body">
                <h3>影响起点</h3>
                <label>
                  选择图节点
                  <select
                    value={current?.id ?? ''}
                    onChange={(event) => {
                      const selected = graph.data!.nodes.find(
                        (item) => item.id === event.target.value,
                      );
                      if (selected) onNode(selected);
                    }}
                  >
                    <option value="">选择影响起点</option>
                    {!fullGraphNode && current && (
                      <option value={current.id}>
                        {nodeKinds[current.kind]} · {current.name}
                        （当前接口范围）
                      </option>
                    )}
                    {graph.data.nodes.map((item) => (
                      <option key={item.id} value={item.id}>
                        {nodeKinds[item.kind]} · {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                {!graph.data.nodes.length && !current && (
                  <p>当前范围没有可选节点，请核对分析覆盖和诊断。</p>
                )}
                {node &&
                  !current &&
                  !(needsScopedGraph && scopedGraph.isPending) && (
                    <p role="alert">
                      所选节点不在全图返回范围；不能据此判断没有影响，请选择当前已返回节点或核对截断限制。
                    </p>
                  )}
                {current && (
                  <>
                    <h4>{current.name}</h4>
                    {current.source_ref && (
                      <ReferenceButton
                        reference={current.source_ref}
                        onSource={onSource}
                      />
                    )}
                    <EvidenceList
                      items={current.evidence}
                      onSource={onSource}
                    />
                  </>
                )}
              </div>
            </nav>
            <div className="surface candidate-impact-results">
              <div className="panel-body">
                {node ? (
                  <NodeImpact
                    key={`${analysis}.${node}`}
                    snapshot={snapshot}
                    analysis={analysis}
                    node={node}
                    candidates={candidates}
                    onCandidates={onCandidates}
                    onSource={onSource}
                  />
                ) : (
                  <p className="panel-empty">
                    从图节点选择影响起点，读取相关接口、请求和前端入口。
                  </p>
                )}
              </div>
            </div>
          </div>
          <div className="surface candidate-review-panel">
            <div className="panel-body">
              {current?.request?.status === 'candidate' && reviewGraph ? (
                <RelationReviews
                  key={`${analysis}:${current.id}`}
                  snapshotId={snapshot}
                  analysisId={analysis}
                  requestId={current.id}
                  graph={reviewGraph}
                  onSource={onSource}
                />
              ) : (
                <>
                  <h3>候选人工决定</h3>
                  <p>
                    {graph.data.nodes.some(
                      (item) => item.request?.status === 'candidate',
                    )
                      ? '选择标记为候选的前端请求，查看目标、决定和历史。'
                      : '当前返回范围没有可处理的候选请求；静态确认请求无需人工决定。'}
                  </p>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
