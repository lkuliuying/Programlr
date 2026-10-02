import { useId, useState } from 'react';
import type {
  Evidence,
  Graph,
  GraphEdge,
  GraphNode,
  RelationDecision,
  SourceRef,
} from '../../shared/api/generated/schema';
import {
  EvidenceList,
  ReferenceButton,
  requestReasons,
  requestStatuses,
} from './AnalysisEvidence';
import './GraphDiagram.css';

const kinds = {
  frontend_function: '前端函数',
  frontend_request: '前端请求',
  endpoint: '接口',
  view: '视图',
  serializer: '序列化器',
  model: '模型',
};
const relations = {
  route_view: '路由绑定',
  serializer_class: '序列化器声明',
  meta_model: '模型声明',
  direct_call: '直接调用',
  contains_function: '包含函数',
  contains_request: '包含请求',
  callback_binding: '框架回调',
  method_path_match: '静态确认',
  candidate_match: '候选匹配',
};
type Decision = Pick<RelationDecision, 'request_id' | 'target_id' | 'decision'>;
type Item = { kind: 'node' | 'edge'; id: string };
function GraphEvidence({
  items,
  onSource,
}: {
  items: Evidence[];
  onSource?: (reference: SourceRef) => void;
}) {
  return onSource ? (
    <EvidenceList items={items} onSource={onSource} />
  ) : (
    <ul className="evidence-list">
      {items.map((item, index) => (
        <li key={index}>
          <code>{item.rule}</code>
          {item.source_ref && (
            <small>
              {item.source_ref.file_path}:{item.source_ref.start_line}–
              {item.source_ref.end_line}
            </small>
          )}
        </li>
      ))}
    </ul>
  );
}
export function GraphDiagram({
  nodes,
  edges,
  reviews = [],
  selected,
  onNode,
  compact = false,
  graph,
  onSource,
  onFullGraph,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  reviews?: Decision[];
  selected?: string | null;
  onNode: (node: GraphNode) => void;
  compact?: boolean;
  graph?: Graph;
  onSource?: (reference: SourceRef) => void;
  onFullGraph?: () => void;
}) {
  const arrow = useId().replace(/:/g, '');
  const [details, setDetails] = useState<{
    selected: string | null | undefined;
    item: Item | null;
  } | null>(null);
  const item =
    details && details.selected === selected
      ? details.item
      : selected
        ? { kind: 'node' as const, id: selected }
        : null;
  const currentNode =
    item?.kind === 'node' ? nodes.find((node) => node.id === item.id) : null;
  const currentEdge =
    item?.kind === 'edge' ? edges.find((edge) => edge.id === item.id) : null;
  const group = (node: GraphNode) =>
    node.kind.startsWith('frontend')
      ? 0
      : node.kind === 'endpoint' || node.kind === 'view'
        ? 1
        : 2;
  const buckets = [0, 1, 2].map((column) =>
    nodes.filter((node) => group(node) === column),
  );
  const preview: GraphNode[] = [];
  for (let row = 0; row < nodes.length && preview.length < 12; row++) {
    for (const bucket of buckets) {
      if (bucket[row] && preview.length < 12) preview.push(bucket[row]);
    }
  }
  const focus = nodes.find((node) => node.id === selected);
  if (focus && !preview.includes(focus))
    preview.splice(Math.max(0, preview.length - 1), 1, focus);
  const shown = compact ? preview : nodes;
  const ids = new Set(shown.map((node) => node.id));
  const shownEdges = edges
    .filter((edge) => ids.has(edge.source_id) && ids.has(edge.target_id))
    .slice(0, compact ? 24 : edges.length);
  const groups = [
    shown.filter((node) => node.kind.startsWith('frontend')),
    shown.filter((node) => node.kind === 'endpoint' || node.kind === 'view'),
    shown.filter((node) => node.kind === 'serializer' || node.kind === 'model'),
  ];
  const positions = new Map(
    groups.flatMap((items, column) =>
      items.map(
        (node, row) =>
          [
            node.id,
            {
              x: compact ? 12 + column * 194 : 24 + column * 406,
              y: compact ? 36 + row * 65 : 50 + row * 86,
            },
          ] as const,
      ),
    ),
  );
  const width = compact ? 592 : 1216;
  const occupied = [new Set<number>(), new Set<number>(), new Set<number>()];
  const routes = shownEdges.map((edge) => {
    const source = positions.get(edge.source_id)!,
      target = positions.get(edge.target_id)!;
    if (compact) {
      const forward = target.x > source.x;
      const sx = source.x + (forward ? 168 : 0),
        tx = target.x + (forward ? 0 : 168);
      const sy = source.y + 25,
        ty = target.y + 25;
      const offset = source.x === target.x ? 42 : (tx - sx) / 2;
      return {
        edge,
        x: 0,
        y: 0,
        path: `M${sx} ${sy}C${sx + offset} ${sy},${tx - offset} ${ty},${tx} ${ty}`,
      };
    }
    const lane = Math.min(
      group(nodes.find((node) => node.id === edge.source_id)!),
      group(nodes.find((node) => node.id === edge.target_id)!),
    );
    const preferred = Math.max(
      0,
      Math.round(((source.y + target.y) / 2 + 25 - 58) / 52),
    );
    let slot = preferred;
    // 同一路径的多条关系使用不同标签位置，确保每条返回边都可单独选择。
    for (let distance = 0; occupied[lane].has(slot); distance++) {
      const above = preferred - distance - 1;
      slot =
        above >= 0 && !occupied[lane].has(above)
          ? above
          : preferred + distance + 1;
    }
    occupied[lane].add(slot);
    const x = 220 + lane * 406,
      y = 42 + slot * 52,
      centerX = x + 80,
      centerY = y + 16;
    const sx = source.x + (source.x < centerX ? 168 : 0),
      tx = target.x + (target.x < centerX ? 168 : 0);
    const sy = source.y + 18,
      ty = target.y + 36;
    return {
      edge,
      x,
      y,
      path: `M${sx} ${sy}C${centerX} ${sy},${centerX} ${centerY},${centerX} ${centerY}C${centerX} ${centerY},${centerX} ${ty},${tx} ${ty}`,
    };
  });
  const height = Math.max(
    130,
    Math.max(...groups.map((items) => items.length)) * (compact ? 65 : 86) + 50,
    ...routes.map((route) => route.y + 60),
  );
  const decision = (edge: GraphEdge) =>
    edge.relation === 'candidate_match'
      ? (reviews.find(
          (review) =>
            review.request_id === edge.source_id &&
            review.target_id === edge.target_id,
        )?.decision ?? 'undecided')
      : 'static';
  const decisionLabel = (edge: GraphEdge) =>
    ({
      confirmed: '人工确认',
      excluded: '人工排除',
      undecided: '未决候选',
      static: compact ? relations[edge.relation] : '静态关系',
    })[decision(edge)];
  return (
    <div className={`graph-presentation${compact ? '' : ' graph-workspace'}`}>
      {compact ? (
        <p className="graph-count">
          展示 {shown.length}/{nodes.length} 个已返回节点 · {shownEdges.length}/
          {edges.length} 条已返回边
        </p>
      ) : (
        <div className="graph-toolbar">
          <div>
            <h2>静态关系图</h2>
            <p className="graph-count">
              已返回 {nodes.length}/{graph?.total_nodes ?? nodes.length} 个节点
              · {edges.length}/{graph?.total_edges ?? edges.length} 条边
              {graph &&
                (graph.endpoint_index === null
                  ? ' · 全图范围'
                  : ` · 接口 ${graph.endpoint_index + 1} 范围`)}
            </p>
          </div>
          <div className="graph-tools">
            {onFullGraph && (
              <button type="button" onClick={onFullGraph}>
                查看全图
              </button>
            )}
            {graph && (
              <details className="graph-coverage">
                <summary>范围与版本</summary>
                <div>
                  <p>静态结果，不代表运行轨迹。</p>
                  <code>
                    {graph.graph_version} · {graph.rule_version}
                  </code>
                  {!graph.coverage.complete && <p>当前返回部分静态结果。</p>}
                  <ul>
                    {graph.coverage.limitations.map((limit, index) => (
                      <li key={index}>{limit}</li>
                    ))}
                  </ul>
                </div>
              </details>
            )}
          </div>
          <div className="graph-legend">
            <span>→ 静态关系</span>
            <span className="accent-text">→ 人工确认</span>
            <span className="warning-text">⇢ 未决候选</span>
            <span className="error-text">⇢ 人工排除</span>
          </div>
          {graph?.truncated && (
            <p role="alert" className="graph-truncation">
              结果已截断：{graph.truncation_reasons.join('、')}
              。未返回范围仍待核对，可选择具体接口缩小范围。
            </p>
          )}
        </div>
      )}
      <div className="graph-stage">
        <div
          className="diagram-scroll"
          tabIndex={0}
          aria-label="静态关系图画布"
        >
          <div className="diagram-canvas" style={{ width, height }}>
            {['前端 · React', '接口与视图 · DRF', '序列化器与模型'].map(
              (label, column) => (
                <span
                  className="graph-group-label"
                  style={{
                    left: compact ? 12 + column * 194 : 24 + column * 406,
                  }}
                  key={label}
                >
                  {label}
                </span>
              ),
            )}
            <svg width={width} height={height} aria-hidden="true">
              <defs>
                <marker
                  id={arrow}
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M0 0L10 5L0 10Z" fill="currentColor" />
                </marker>
              </defs>
              {routes.map(({ edge, path }) => (
                <path
                  key={edge.id}
                  className={`graph-edge edge-${decision(edge)}${currentEdge?.id === edge.id ? ' graph-edge-active' : ''}`}
                  d={path}
                  markerEnd={`url(#${arrow})`}
                >
                  <title>{decisionLabel(edge)}</title>
                </path>
              ))}
            </svg>
            {!compact &&
              routes.map(({ edge, x, y }, index) => {
                const label = `${nodes.find((node) => node.id === edge.source_id)?.name} → ${nodes.find((node) => node.id === edge.target_id)?.name} · ${relations[edge.relation]} · ${decisionLabel(edge)}`;
                return (
                  <button
                    type="button"
                    key={edge.id}
                    className={`graph-edge-label edge-label-${decision(edge)}`}
                    style={{ left: x, top: y }}
                    title={label}
                    aria-label={`关系 ${index + 1}：${label}`}
                    aria-pressed={currentEdge?.id === edge.id}
                    onClick={() =>
                      setDetails({
                        selected,
                        item: { kind: 'edge', id: edge.id },
                      })
                    }
                  >
                    <span>
                      {index + 1} · {relations[edge.relation]}
                    </span>
                    <small>{decisionLabel(edge)}</small>
                  </button>
                );
              })}
            {shown.map((node) => {
              const position = positions.get(node.id)!;
              return (
                <button
                  key={node.id}
                  type="button"
                  className={`graph-node node-${node.kind}`}
                  style={{ left: position.x, top: position.y }}
                  title={
                    node.source_ref
                      ? `${node.name} · ${node.source_ref.file_path}:${node.source_ref.start_line}`
                      : node.name
                  }
                  aria-pressed={node.id === selected}
                  onClick={() => {
                    if (!compact)
                      setDetails({
                        selected,
                        item: { kind: 'node', id: node.id },
                      });
                    onNode(node);
                  }}
                >
                  <strong>{node.name}</strong>
                  <small>
                    {kinds[node.kind]}
                    {node.request &&
                      ` · ${{ confirmed: '静态确认', candidate: '候选，待确认', unmatched: '未匹配' }[node.request.status]}`}
                  </small>
                </button>
              );
            })}
          </div>
        </div>
        {!compact && item && (
          <aside className="graph-inspector" aria-label="图内依据">
            <div className="graph-inspector-title">
              <h3>{currentEdge ? '关系依据' : '节点依据'}</h3>
              <button
                type="button"
                aria-label="关闭图内依据"
                onClick={() => setDetails({ selected, item: null })}
              >
                ×
              </button>
            </div>
            {currentNode ? (
              <>
                <h4>{currentNode.name}</h4>
                <p>{kinds[currentNode.kind]}</p>
                {currentNode.source_ref &&
                  (onSource ? (
                    <ReferenceButton
                      reference={currentNode.source_ref}
                      onSource={onSource}
                    />
                  ) : (
                    <code>
                      {currentNode.source_ref.file_path}:
                      {currentNode.source_ref.start_line}–
                      {currentNode.source_ref.end_line}
                    </code>
                  ))}
                {currentNode.request && (
                  <p>
                    {requestStatuses[currentNode.request.status]} ·{' '}
                    {requestReasons[currentNode.request.reason] ??
                      currentNode.request.reason}
                    <br />
                    原路径：
                    <code>{currentNode.request.original_path ?? '动态'}</code>
                    <br />
                    目标路径：<code>{currentNode.request.path ?? '未知'}</code>
                  </p>
                )}
                <GraphEvidence
                  items={currentNode.evidence}
                  onSource={onSource}
                />
              </>
            ) : currentEdge ? (
              <>
                <h4>
                  {relations[currentEdge.relation]} ·{' '}
                  {decisionLabel(currentEdge)}
                </h4>
                <p>
                  {
                    nodes.find((node) => node.id === currentEdge.source_id)
                      ?.name
                  }{' '}
                  →{' '}
                  {
                    nodes.find((node) => node.id === currentEdge.target_id)
                      ?.name
                  }
                </p>
                <GraphEvidence
                  items={currentEdge.evidence}
                  onSource={onSource}
                />
                {currentEdge.relation === 'candidate_match' && (
                  <p className="muted">
                    人工确认、排除和撤销请在候选影响模块处理。
                  </p>
                )}
              </>
            ) : (
              <p role="alert">所选节点不在当前返回范围，请重新选择。</p>
            )}
          </aside>
        )}
      </div>
      {!shown.length && (
        <p className="panel-empty">
          当前范围没有返回节点，不能据此判断不存在关系。
        </p>
      )}
      {compact && (
        <div className="graph-legend">
          <span>→ 静态关系</span>
          <span className="accent-text">→ 人工确认</span>
          <span className="warning-text">⇢ 未决候选</span>
          <span className="error-text">⇢ 人工排除</span>
        </div>
      )}
      {compact && (
        <details className="graph-edge-list">
          <summary>关系列表与状态（{shownEdges.length}）</summary>
          <ul>
            {shownEdges.map((edge) => (
              <li key={edge.id}>
                {nodes.find((node) => node.id === edge.source_id)?.name} →{' '}
                {nodes.find((node) => node.id === edge.target_id)?.name} ·{' '}
                {decisionLabel(edge)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
