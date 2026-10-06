import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Tag } from 'antd';
import type {
  Endpoint,
  GraphNode,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import {
  RecordList,
  type RecordColumn,
} from '../../shared/components/RecordList';
import {
  AnalysisCoverage,
  DiagnosticsPanel,
  EvidenceList,
  ReferenceButton,
  requestReasons,
  requestStatuses,
} from './AnalysisEvidence';
import { getAnalysis, listEndpoints } from './api/analysis-api';

export function AnalysisBrowser({
  snapshotId,
  analysisId,
  endpoint,
  onEndpoint,
  onSource,
}: {
  snapshotId: string;
  analysisId: string;
  endpoint: number | null;
  nodeId: string | null;
  onEndpoint: (index: number | null) => void;
  onNode: (node: GraphNode) => void;
  onSource: (reference: SourceRef) => void;
}) {
  const [page, setPage] = useState(1);
  const analysis = useQuery({
    queryKey: ['analysis', snapshotId, analysisId],
    queryFn: ({ signal }) => getAnalysis(snapshotId, analysisId, signal),
  });
  const endpoints = useQuery({
    queryKey: ['analysis', snapshotId, analysisId, 'endpoints', page],
    queryFn: ({ signal }) =>
      listEndpoints(snapshotId, analysisId, page, signal),
    enabled: !!analysis.data,
  });
  const selectedPage = endpoint === null ? page : Math.floor(endpoint / 20) + 1;
  const selectedEndpoints = useQuery({
    queryKey: ['analysis', snapshotId, analysisId, 'endpoints', selectedPage],
    queryFn: ({ signal }) =>
      listEndpoints(snapshotId, analysisId, selectedPage, signal),
    enabled: !!analysis.data && endpoint !== null,
  });
  const selected = selectedEndpoints.data?.results.find(
    (item) => item.index === endpoint,
  );
  const endpointTitle = (item: Endpoint) => (
    <button
      type="button"
      className="record-choice"
      aria-current={item.index === endpoint ? 'true' : undefined}
      onClick={() => onEndpoint(item.index)}
    >
      <strong>{item.method}</strong> <code>{item.path}</code>
    </button>
  );
  const endpointColumns: RecordColumn<Endpoint>[] = [
    { key: 'endpoint', title: '方法与路径', render: endpointTitle },
    {
      key: 'action',
      title: '处理动作',
      width: 140,
      render: (item) => <code>{item.action}</code>,
    },
    {
      key: 'frontend',
      title: '前端关联',
      width: 180,
      render: (item) =>
        item.frontend_available
          ? `${item.frontend_links.filter((link) => link.status === 'confirmed').length} 确认 · ${item.frontend_links.filter((link) => link.status === 'candidate').length} 候选`
          : '历史记录未分析前端',
    },
  ];
  return (
    <section aria-label="API 分析详情">
      <Feedback
        error={analysis.error}
        retry={() => {
          void analysis.refetch();
        }}
      />
      {analysis.isPending && <p role="status">正在读取接口分析记录…</p>}
      {analysis.data && (
        <>
          <AnalysisCoverage analysis={analysis.data} />
          <div className="analysis-columns api-analysis-columns">
            <nav className="endpoint-nav" aria-label="接口导航">
              <h3>接口清单</h3>
              <Button
                onClick={() => onEndpoint(null)}
                disabled={endpoint === null}
              >
                清除接口选择
              </Button>
              <Feedback
                error={endpoints.error}
                retry={() => {
                  void endpoints.refetch();
                }}
              />
              {endpoints.isPending && <p role="status">加载接口清单…</p>}
              {endpoints.data && (
                <RecordList
                  label="接口清单"
                  records={endpoints.data.results}
                  columns={endpointColumns}
                  rowKey={(item) => String(item.index)}
                  recordTitle={endpointTitle}
                  titleColumnKey="endpoint"
                  selectedKey={endpoint === null ? undefined : String(endpoint)}
                  empty={
                    endpoints.data.count
                      ? '当前批次没有接口记录，请查看其他批次。'
                      : '当前规则未发现后端接口，请核对诊断与覆盖限制。'
                  }
                />
              )}
              {endpoints.data && (
                <>
                  <PageControls
                    page={page}
                    {...endpoints.data}
                    onPage={setPage}
                  />
                </>
              )}
            </nav>
            <section className="relation-flow" aria-label="接口定义与前端来源">
              {endpoint === null ? (
                <>
                  <h3>选择接口阅读定义</h3>
                  <p>
                    从清单选择方法与路径，核对处理视图、序列化器和前端请求来源。
                  </p>
                </>
              ) : (
                <>
                  <Feedback
                    error={selectedEndpoints.error}
                    retry={() => {
                      void selectedEndpoints.refetch();
                    }}
                  />
                  {selectedEndpoints.isPending && (
                    <p role="status">读取所选接口定义…</p>
                  )}
                  {selected && (
                    <EndpointDetails endpoint={selected} onSource={onSource} />
                  )}
                  {selectedEndpoints.data && !selected && (
                    <p role="alert">所选接口不在此分析记录中，请重新选择。</p>
                  )}
                </>
              )}
            </section>
            <aside className="relation-evidence" aria-label="接口分析诊断">
              <details>
                <summary>诊断与缺口</summary>
                <DiagnosticsPanel
                  snapshotId={snapshotId}
                  analysisId={analysisId}
                  onSource={onSource}
                />
              </details>
            </aside>
          </div>
        </>
      )}
    </section>
  );
}

function EndpointDetails({
  endpoint,
  onSource,
}: {
  endpoint: Endpoint;
  onSource: (reference: SourceRef) => void;
}) {
  return (
    <>
      <h3>
        <Tag>{endpoint.method}</Tag> <code>{endpoint.path}</code>
      </h3>
      <p>
        处理动作：<code>{endpoint.action}</code> · 路由形式：
        {endpoint.path_kind}
      </p>
      <dl className="endpoint-definition">
        {(
          [
            ['处理视图', endpoint.view],
            ['序列化器', endpoint.serializer],
            ['数据模型', endpoint.model],
          ] as const
        ).map(([label, symbol]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>
              {symbol ? (
                <>
                  <strong>{symbol.name}</strong>
                  <ReferenceButton
                    reference={symbol.source_ref}
                    onSource={onSource}
                  />
                </>
              ) : (
                '当前规则未识别，不能据此判断不存在。'
              )}
            </dd>
          </div>
        ))}
      </dl>
      <h4>接口定义依据</h4>
      <EvidenceList items={endpoint.evidence} onSource={onSource} />
      <h4>前端请求来源</h4>
      {!endpoint.frontend_available ? (
        <p>此历史记录未分析前端，读取不会触发重新分析。</p>
      ) : !endpoint.frontend_links.length ? (
        <p>当前规则未找到关联前端请求，不能据此判断没有调用入口。</p>
      ) : (
        <ul className="evidence-list">
          {endpoint.frontend_links.map((link) => (
            <li key={link.request_id}>
              <Tag>{requestStatuses[link.status]}</Tag>
              <code>
                {link.method ?? '未知方法'} {link.path ?? '动态路径'}
              </code>
              <p>{requestReasons[link.reason] ?? link.reason}</p>
              <ReferenceButton
                reference={link.source_ref}
                onSource={onSource}
              />
              {link.relation_review && (
                <p>
                  {
                    {
                      confirmed: '人工确认',
                      excluded: '人工排除',
                      undecided: '未决候选',
                    }[link.relation_review.decision]
                  }{' '}
                  · 修订 {link.relation_review.revision} ·
                  历史人工决定只读，校准写入已退役。
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="muted">
        请求字段与响应规则请打开序列化器和视图源码核对；源码关联可在工作区关系面板查看。
      </p>
    </>
  );
}
