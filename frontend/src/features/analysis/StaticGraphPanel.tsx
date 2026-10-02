import { useQuery } from '@tanstack/react-query';
import type { GraphNode, SourceRef } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { GraphDiagram } from './GraphDiagram';
import { getGraph } from './api/analysis-api';

type Selection = {
  snapshot: string;
  analysis: string;
  endpoint: number | null;
};
export function StaticGraphPanel({
  selected,
  node,
  onNode,
  onSource,
  onFullGraph,
}: {
  selected: Selection | null;
  node: string | null;
  onNode: (node: GraphNode) => void;
  onSource: (reference: SourceRef) => void;
  onFullGraph?: () => void;
}) {
  const graph = useQuery({
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
  return (
    <section className="static-graph-panel" aria-label="静态关系图">
      {!selected ? (
        <p className="panel-empty">
          选择快照并显式提交分析，查看有依据的前后端关系。
        </p>
      ) : (
        <>
          <Feedback
            error={graph.error}
            retry={() => {
              void graph.refetch();
            }}
          />
          {graph.isPending && <p role="status">读取静态关系图…</p>}
          {graph.data && (
            <GraphDiagram
              key={`${graph.data.analysis_id}:${graph.data.endpoint_index}`}
              graph={graph.data}
              nodes={graph.data.nodes}
              edges={graph.data.edges}
              reviews={graph.data.relation_reviews}
              selected={node}
              onNode={onNode}
              onSource={onSource}
              onFullGraph={onFullGraph}
            />
          )}
        </>
      )}
    </section>
  );
}
