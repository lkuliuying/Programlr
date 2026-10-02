import { afterEach, expect, test, vi } from 'vitest';
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
import type { GraphEdge, GraphNode } from '../../shared/api/generated/schema';
import { GraphDiagram } from './GraphDiagram';
afterEach(cleanup);
const id = (i: number) =>
  `00000000-0000-0000-0000-${String(i).padStart(12, '0')}`;
const nodes: GraphNode[] = Array.from({ length: 30 }, (_, i) => ({
  id: id(i),
  kind: i < 10 ? 'frontend_request' : i < 20 ? 'endpoint' : 'model',
  name: `节点 ${i}`,
  source_ref: null,
  evidence: [],
  endpoint: null,
  request:
    i < 10
      ? {
          method: 'GET',
          original_path: '/a',
          path: '/a',
          status: 'candidate',
          reason: 'unknown_base',
        }
      : null,
}));
test('总览展示预算、分组与选中节点，边和关系列表保持一致', () => {
  const edges: GraphEdge[] = Array.from({ length: 40 }, (_, i) => ({
    id: id(100 + i),
    source_id: id(i % 4),
    target_id: id(10 + (i % 4)),
    relation: 'candidate_match',
    evidence: [],
  }));
  const onNode = vi.fn();
  const { container } = render(
    <GraphDiagram
      nodes={nodes}
      edges={edges}
      selected={id(29)}
      compact
      onNode={onNode}
      reviews={[
        { request_id: id(0), target_id: id(10), decision: 'excluded' },
        { request_id: id(1), target_id: id(11), decision: 'confirmed' },
      ]}
    />,
  );
  expect(screen.getAllByRole('button')).toHaveLength(12);
  expect(
    screen.getByText('展示 12/30 个已返回节点 · 24/40 条已返回边'),
  ).toBeTruthy();
  expect(container.querySelectorAll('.graph-edge')).toHaveLength(24);
  expect(container.querySelectorAll('.graph-edge-list li')).toHaveLength(24);
  expect(container.querySelector('.edge-excluded')).toBeTruthy();
  expect(container.querySelector('.edge-confirmed')).toBeTruthy();
  expect(container.querySelector('.edge-undecided')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: /节点 29/ }));
  expect(onNode).toHaveBeenCalledWith(nodes[29]);
});
test('空图保留范围限制，不推出不存在关系', () => {
  render(<GraphDiagram nodes={[]} edges={[]} onNode={() => {}} />);
  expect(screen.getByText(/不能据此判断不存在关系/)).toBeTruthy();
});

test('完整图保留全部返回节点和边，每条关系可独立选择依据并关闭', () => {
  const reference = {
    snapshot_id: id(999),
    file_path: 'views.py',
    start_line: 2,
    end_line: 3,
  };
  const fullNodes = Array.from({ length: 100 }, (_, i) => ({
    ...nodes[i % nodes.length],
    id: id(i),
    name: `节点 ${i}`,
  }));
  const edges: GraphEdge[] = Array.from({ length: 200 }, (_, i) => ({
    id: id(100 + i),
    source_id: id(i % 100),
    target_id: id((i + 1) % 100),
    relation: i < 3 ? 'candidate_match' : 'direct_call',
    evidence: [
      { kind: 'source_fact', rule: `关系规则 ${i}`, source_ref: reference },
    ],
  }));
  const onNode = vi.fn(),
    onSource = vi.fn();
  const { container, rerender } = render(
    <GraphDiagram
      nodes={fullNodes}
      edges={edges}
      selected={null}
      onNode={onNode}
      onSource={onSource}
      reviews={[
        { request_id: id(0), target_id: id(1), decision: 'excluded' },
        { request_id: id(1), target_id: id(2), decision: 'confirmed' },
      ]}
    />,
  );
  expect(container.querySelectorAll('.graph-node')).toHaveLength(100);
  expect(container.querySelectorAll('.graph-edge')).toHaveLength(200);
  const labels = screen.getAllByRole('button', { name: /^关系 \d+：/ });
  expect(labels).toHaveLength(200);
  expect(new Set(labels.map((label) => label.getAttribute('style'))).size).toBe(
    200,
  );
  expect(
    new Set(
      [...container.querySelectorAll('.graph-edge')].map((path) =>
        path.getAttribute('d'),
      ),
    ).size,
  ).toBe(200);
  expect(container.querySelector('.edge-label-excluded')).toBeTruthy();
  expect(container.querySelector('.edge-label-confirmed')).toBeTruthy();
  expect(container.querySelector('.edge-label-undecided')).toBeTruthy();
  expect(container.querySelector('.edge-label-static')).toBeTruthy();
  expect(container.querySelector('.graph-edge-list')).toBeNull();
  fireEvent.click(labels[199]);
  const inspector = screen.getByRole('complementary', { name: '图内依据' });
  expect(within(inspector).getByText('关系规则 199')).toBeTruthy();
  expect(labels[199].getAttribute('aria-pressed')).toBe('true');
  expect(container.querySelectorAll('.graph-edge-active')).toHaveLength(1);
  expect(onNode).not.toHaveBeenCalled();
  fireEvent.click(
    within(inspector).getByRole('button', { name: 'views.py:2–3' }),
  );
  expect(onSource).toHaveBeenCalledWith(reference);
  fireEvent.click(screen.getByRole('button', { name: '关闭图内依据' }));
  expect(screen.queryByRole('complementary', { name: '图内依据' })).toBeNull();
  expect(labels[199].getAttribute('aria-pressed')).toBe('false');
  fireEvent.click(screen.getByRole('button', { name: /^节点 99/ }));
  expect(onNode).toHaveBeenCalledWith(fullNodes[99]);
  expect(
    screen.getAllByRole('complementary', { name: '图内依据' }),
  ).toHaveLength(1);
  fireEvent.click(labels[0]);
  expect(
    screen.getAllByRole('complementary', { name: '图内依据' }),
  ).toHaveLength(1);
  expect(screen.getByText('关系规则 0')).toBeTruthy();
  rerender(
    <GraphDiagram
      nodes={fullNodes}
      edges={edges}
      selected={id(5)}
      onNode={onNode}
      onSource={onSource}
    />,
  );
  expect(
    within(screen.getByRole('complementary', { name: '图内依据' })).getByRole(
      'heading',
      { name: '节点 5' },
    ),
  ).toBeTruthy();
  expect(screen.queryByText('关系规则 0')).toBeNull();
});
