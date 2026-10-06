import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type { GraphNode, SourceRef } from '../../shared/api/generated/schema';
import { requestJson } from '../../shared/api/client';
import * as v from '../../shared/api/validation';
import { Feedback } from '../../shared/components/Feedback';
import { WorkspaceDialog } from '../../shared/components/WorkspaceDialog';
import { parseGraph } from './api/analysis-api';
import { GraphDiagram } from './GraphDiagram';
import { StaticGraphPanel } from './StaticGraphPanel';

export function RelationsPanel({
  selected,
  node,
  onNode,
  onSource,
}: {
  selected: {
    snapshot: string;
    analysis: string;
    endpoint: number | null;
  } | null;
  node: string | null;
  onNode: (node: GraphNode) => void;
  onSource: (source: SourceRef) => void;
}) {
  const [view, setView] = useState<'interfaces' | 'dependencies'>('interfaces');
  const [expanded, setExpanded] = useState(false);
  const graph = useQuery({
    queryKey: [
      'analysis',
      selected?.analysis,
      'endpoint-relations',
      selected?.endpoint,
    ],
    queryFn: ({ signal }) =>
      requestJson(
        `/api/v1/analyses/${selected!.analysis}/endpoint-relations/${selected!.endpoint === null ? '' : '?endpoint_index=' + selected!.endpoint}`,
        (raw) => ({
          ...parseGraph(
            raw,
            selected!.snapshot,
            selected!.analysis,
            selected!.endpoint,
          ),
          direction: v.oneOf(v.object(raw).direction, ['undirected']),
          scope: v.oneOf(v.object(raw).scope, [
            'connected_shared_symbols',
            'all_shared_symbols',
          ]),
        }),
        { signal },
      ),
    enabled: !!selected && view === 'interfaces',
  });
  const diagram = graph.data && (
    <GraphDiagram
      graph={graph.data}
      nodes={graph.data.nodes}
      edges={graph.data.edges}
      selected={node}
      onNode={onNode}
      onSource={onSource}
      compact={false}
      undirected
    />
  );
  return (
    <section aria-label="接口与代码关系">
      <h2>关系</h2>
      <div className="mainline-choice" role="group" aria-label="关系视图">
        <Button
          aria-pressed={view === 'interfaces'}
          onClick={() => setView('interfaces')}
        >
          接口关联
        </Button>
        <Button
          aria-pressed={view === 'dependencies'}
          onClick={() => setView('dependencies')}
        >
          代码依赖
        </Button>
      </div>
      {view === 'interfaces' ? (
        <>
          <p>
            接口通过共用的处理器、序列化器或模型关联。连接表示源码关系；业务执行顺序需结合源码理解。
          </p>
          <Feedback error={graph.error} retry={() => void graph.refetch()} />
          {!selected && <p>接口分析完成后可查看关联。</p>}
          {selected && graph.isPending && <p role="status">读取接口关联…</p>}
          {graph.data && (
            <>
              <p>
                范围：
                {graph.data.scope === 'all_shared_symbols'
                  ? '全分析共享符号'
                  : '所选接口的共享符号连通范围'}{' '}
                · 无向源码关联
                {' · '}
                {graph.data.nodes.length}/{graph.data.total_nodes} 个节点
                {' · '}
                {graph.data.edges.length}/{graph.data.total_edges} 条边
              </p>
              {graph.data.truncated && (
                <p role="alert">
                  结果已截断：{graph.data.truncation_reasons.join('、')}
                  。可选择具体接口缩小范围。
                </p>
              )}
              <Button onClick={() => setExpanded(true)}>展开关系图</Button>
              {!expanded && diagram}
            </>
          )}
          <WorkspaceDialog
            open={expanded}
            title="接口关联图"
            onClose={() => setExpanded(false)}
          >
            {expanded && diagram}
          </WorkspaceDialog>
        </>
      ) : (
        <StaticGraphPanel
          selected={selected}
          node={node}
          onNode={onNode}
          onSource={onSource}
        />
      )}
    </section>
  );
}
