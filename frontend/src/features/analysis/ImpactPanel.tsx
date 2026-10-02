import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Tag } from 'antd';
import type {
  Impact,
  SnapshotComparison,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { getImpact, getComparisonImpact } from './api/impact-api';

type Source = (ref: SourceRef, analysis: string) => void;
export function NodeImpact({
  snapshot,
  analysis,
  node,
  candidates,
  onCandidates,
  onSource,
}: {
  snapshot: string;
  analysis: string;
  node: string;
  candidates: boolean;
  onCandidates: (value: boolean) => void;
  onSource: Source;
}) {
  const query = useQuery({
    queryKey: ['impact', analysis, node, candidates],
    queryFn: ({ signal }) =>
      getImpact(snapshot, analysis, node, candidates, signal),
  });
  return (
    <section aria-label="节点候选影响">
      <h3>节点候选影响</h3>
      <CandidateSwitch value={candidates} onChange={onCandidates} />
      <Button
        onClick={() => {
          void query.refetch();
        }}
      >
        刷新影响与人工决定
      </Button>
      <Feedback error={query.error} />
      {query.isPending && <p role="status">计算有界静态范围…</p>}
      {query.data && (
        <ImpactResults
          key={`${analysis}.${node}.${candidates}`}
          data={query.data}
          onSource={onSource}
        />
      )}
    </section>
  );
}
export function ComparisonImpactPanel({
  comparison,
  change,
  candidates,
  onCandidates,
  onSource,
}: {
  comparison: SnapshotComparison;
  change: string | null;
  candidates: boolean;
  onCandidates: (value: boolean) => void;
  onSource: Source;
}) {
  const query = useQuery({
    queryKey: ['impact', 'comparison', comparison.id, change, candidates],
    queryFn: ({ signal }) =>
      getComparisonImpact(comparison, change, candidates, signal),
  });
  return (
    <section aria-label="对比候选影响">
      <h3>两侧候选影响</h3>
      <p>{change ? '当前文件变化' : '全部文件变化'}；基准与目标分别计算。</p>
      <CandidateSwitch value={candidates} onChange={onCandidates} />
      <Button
        onClick={() => {
          void query.refetch();
        }}
      >
        刷新影响与人工决定
      </Button>
      <Feedback error={query.error} />
      {query.data && (
        <>
          {query.data.limitations.map((x, i) => (
            <p key={i}>{x}</p>
          ))}
          <div className="comparison-sources">
            {(['base', 'target'] as const).map((side) => {
              const data = query.data![side];
              return (
                <section key={side}>
                  <h4>{side === 'base' ? '基准影响' : '目标影响'}</h4>
                  <p>
                    变化文件：
                    {data.changed_files.join('、') || '当前选择无变更位置'}
                  </p>
                  {data.impact ? (
                    <ImpactResults
                      key={`${comparison.id}.${change}.${candidates}.${side}`}
                      data={data.impact}
                      onSource={onSource}
                    />
                  ) : (
                    <p>{data.reason}</p>
                  )}
                </section>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
function CandidateSwitch({
  value,
  onChange,
}: {
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label>
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
      包含未决候选（人工排除仍不参与）
    </label>
  );
}
export function ImpactResults({
  data,
  onSource,
}: {
  data: Impact;
  onSource: Source;
}) {
  const [page, setPage] = useState(1),
    nodes = new Map(data.nodes.map((x) => [x.id, x])),
    edges = new Map(data.edges.map((x) => [x.id, x]));
  const choices = new Map(
    data.relation_reviews.map((x) => [`${x.request_id}:${x.target_id}`, x]),
  );
  return (
    <>
      <p>
        访问 {data.visited_nodes}/{data.max_nodes} 个节点、{data.visited_edges}/
        {data.max_edges} 条边 · 找到 {data.results.length}{' '}
        个接口、请求或前端入口
      </p>
      {data.truncated && (
        <p role="alert">
          结果已截断：{data.truncation_reasons.join('、')}，剩余范围未判断。
        </p>
      )}
      {!data.results.length && (
        <p>当前图和预算内未找到相关入口，不能说明没有影响。</p>
      )}
      {data.results.slice((page - 1) * 20, page * 20).map((item) => (
        <details key={item.node.id}>
          <summary>
            {item.node.name}{' '}
            <Tag>
              {item.via_candidate ? '依赖未决候选' : '静态或人工确认路径'}
            </Tag>
          </summary>
          <ol>
            {item.path_node_ids.map((id, i) => {
              const node = nodes.get(id)!,
                edge = edges.get(item.path_edge_ids[i]),
                choice = edge
                  ? choices.get(`${edge.source_id}:${edge.target_id}`)
                  : null;
              return (
                <li key={id}>
                  {node.kind} · {node.name}
                  {node.source_ref && (
                    <button
                      type="button"
                      onClick={() =>
                        onSource(node.source_ref!, data.analysis_id)
                      }
                    >
                      {node.source_ref.file_path}:{node.source_ref.start_line}
                    </button>
                  )}
                  {edge && (
                    <>
                      <p>
                        → {edge.relation}
                        {choice &&
                          ` · ${choice.decision === 'confirmed' ? '人工确认' : '未决候选'} · 修订 ${choice.revision}`}
                      </p>
                      <ul>
                        {edge.evidence.map((proof, index) => (
                          <li key={index}>
                            {proof.rule}
                            {proof.source_ref && (
                              <button
                                type="button"
                                onClick={() =>
                                  onSource(proof.source_ref!, data.analysis_id)
                                }
                              >
                                {proof.source_ref.file_path}:
                                {proof.source_ref.start_line}
                              </button>
                            )}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </li>
              );
            })}
          </ol>
        </details>
      ))}
      <PageControls
        page={page}
        next={page * 20 < data.results.length ? 'next' : null}
        previous={page > 1 ? 'previous' : null}
        onPage={setPage}
      />
      <details>
        <summary>覆盖限制与未解析关系</summary>
        {data.limitations.map((x, i) => (
          <p key={i}>{x}</p>
        ))}
        <p>
          变更位置未映射的文件：{data.unmapped_files.join('、') || '当前无记录'}
        </p>
        <p>
          图中无引用的导入文件：
          {data.uncovered_files.join('、') || '当前无记录'}
        </p>
        {data.diagnostics.map((x, i) => (
          <p key={i}>
            {x.code} · {x.message}
            {x.source_ref && (
              <button
                type="button"
                onClick={() => onSource(x.source_ref!, data.analysis_id)}
              >
                {x.source_ref.file_path}:{x.source_ref.start_line}
              </button>
            )}
          </p>
        ))}
      </details>
    </>
  );
}
