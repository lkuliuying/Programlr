import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tag } from 'antd';
import type {
  Analysis,
  Evidence,
  Graph,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { listDiagnostics } from './api/analysis-api';

export const nodeKinds = {
  frontend_function: '前端函数',
  frontend_request: '前端请求',
  endpoint: '接口',
  view: '视图',
  serializer: '序列化器',
  model: '模型',
};
export const relationLabels = {
  route_view: '路由绑定',
  serializer_class: '序列化器声明',
  meta_model: '模型声明',
  direct_call: '直接调用',
  contains_function: '源码包含函数',
  contains_request: '源码包含请求',
  callback_binding: '框架回调分派',
  method_path_match: '方法与路径确认',
  candidate_match: '候选匹配',
};
export const requestStatuses = {
  confirmed: '静态确认',
  candidate: '候选，待确认',
  unmatched: '未匹配',
};
export const requestReasons: Record<string, string> = {
  unique_method_path: '方法与完整路径唯一匹配',
  multiple_endpoints: '存在多个后端目标',
  unknown_base: '基础地址未知',
  dynamic: '路径或配置为动态值',
  external: '外部地址，无法确认本地目标',
  unsupported: '超出当前规则',
  no_matching_endpoint: '没有匹配的后端接口',
};
export function ReferenceButton({
  reference,
  onSource,
}: {
  reference: SourceRef;
  onSource: (reference: SourceRef) => void;
}) {
  return (
    <button
      type="button"
      className="source-link"
      onClick={() => onSource(reference)}
    >
      {reference.file_path}:{reference.start_line}–{reference.end_line}
    </button>
  );
}
export function EvidenceList({
  items,
  onSource,
}: {
  items: Evidence[];
  onSource: (reference: SourceRef) => void;
}) {
  return (
    <ul className="evidence-list">
      {items.map((item, index) => (
        <li key={index}>
          <Tag>
            {
              {
                source_fact: '源码事实',
                static_inference: '静态推断',
                framework_rule: '框架规则',
              }[item.kind]
            }
          </Tag>
          <code>{item.rule}</code>
          {item.source_ref ? (
            <ReferenceButton reference={item.source_ref} onSource={onSource} />
          ) : (
            <small>此依据没有源码位置。</small>
          )}
        </li>
      ))}
    </ul>
  );
}
export function AnalysisCoverage({ analysis }: { analysis: Analysis }) {
  return (
    <div className="analysis-summary">
      <p>
        根路由：<code>{analysis.root_urlconf}</code> ·
        静态结果，不代表运行轨迹。
      </p>
      {analysis.frontend ? (
        <p>
          {analysis.frontend.coverage.source_files} 个前端文件 ·{' '}
          {analysis.frontend.confirmed} 个确认请求 ·{' '}
          {analysis.frontend.candidate} 个候选 · {analysis.frontend.unmatched}{' '}
          个未匹配
          {!analysis.frontend.coverage.request_count &&
            ' · 当前规则下没有识别到前端请求'}
        </p>
      ) : (
        <p className="pending-note">
          此历史记录未分析前端。读取不会触发重新分析。
        </p>
      )}
      {!analysis.coverage.complete && (
        <p className="pending-note">部分分析结果，请结合诊断与覆盖说明阅读。</p>
      )}
      <details>
        <summary>覆盖范围与规则版本</summary>
        <code>
          {analysis.rule_version}
          {analysis.frontend &&
            ` · ${analysis.frontend.rule_version} · ${analysis.frontend.association_rule_version}`}
        </code>
        <ul>
          {[
            ...analysis.coverage.limitations,
            ...(analysis.frontend?.coverage.limitations ?? []),
          ].map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
export function GraphScopeNote({ graph }: { graph: Graph }) {
  return (
    <div className="graph-scope-note">
      <p>
        已返回 {graph.returned_nodes}/{graph.total_nodes} 个节点、
        {graph.returned_edges}/{graph.total_edges} 条边 ·
        静态结果，不代表运行轨迹。
      </p>
      {graph.truncated && (
        <p role="alert" className="pending-note">
          结果已截断：{graph.truncation_reasons.join('、')}
          。未返回范围仍待核对，可选择具体接口缩小关系范围。
        </p>
      )}
      {!graph.coverage.complete && (
        <p className="pending-note">部分静态结果，请结合覆盖限制和诊断核对。</p>
      )}
      <details>
        <summary>图版本与覆盖限制</summary>
        <code>
          {graph.graph_version} · {graph.rule_version}
        </code>
        <ul>
          {graph.coverage.limitations.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}
export function DiagnosticsPanel({
  snapshotId,
  analysisId,
  onSource,
}: {
  snapshotId: string;
  analysisId: string;
  onSource: (reference: SourceRef) => void;
}) {
  const [page, setPage] = useState(1);
  const diagnostics = useQuery({
    queryKey: ['analysis', snapshotId, analysisId, 'diagnostics', page],
    queryFn: ({ signal }) =>
      listDiagnostics(snapshotId, analysisId, page, signal),
  });
  return (
    <section aria-label="诊断与缺口">
      <h3>诊断与缺口</h3>
      <Feedback
        error={diagnostics.error}
        retry={() => {
          void diagnostics.refetch();
        }}
      />
      {diagnostics.isPending && <p role="status">加载诊断…</p>}
      {diagnostics.data && (
        <>
          {!diagnostics.data.count && (
            <p>未报告额外诊断。静态分析仍受规则范围限制。</p>
          )}
          <ul className="evidence-list">
            {diagnostics.data.results.map((item, index) => (
              <li key={index}>
                <strong>{item.code}</strong>
                <p>{item.message}</p>
                {item.source_ref && (
                  <ReferenceButton
                    reference={item.source_ref}
                    onSource={onSource}
                  />
                )}
              </li>
            ))}
          </ul>
          <PageControls page={page} {...diagnostics.data} onPage={setPage} />
        </>
      )}
    </section>
  );
}
