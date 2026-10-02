import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Icon } from '../../shared/components/Icon';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { listSnapshots } from './api/projects-api';
import { snapshotDisplayName } from './snapshot-name';
export function SnapshotTimeline({
  project,
  selected,
  onSelect,
  onCompare,
  children,
}: {
  project: string;
  selected: string | null;
  onSelect: (id: string) => void;
  onCompare: () => void;
  children?: React.ReactNode;
}) {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ['projects', 'snapshots', project, page],
    queryFn: ({ signal }) => listSnapshots(project, page, signal),
  });
  return (
    <section className="surface snapshot-timeline" aria-label="快照历史总览">
      <div className="panel-title">
        <Icon name="comparison" />
        <h2>快照历史与对比</h2>
        <button className="text-button" onClick={onCompare}>
          创建对比
        </button>
      </div>
      <div className="panel-body">
        <Feedback error={query.error} />
        {query.isPending && <p role="status">读取快照历史…</p>}
        <ol>
          {query.data?.results.map((snapshot) => (
            <li key={snapshot.id} data-current={snapshot.id === selected}>
              <button
                className="timeline-entry"
                aria-current={snapshot.id === selected ? 'true' : undefined}
                onClick={() => onSelect(snapshot.id)}
              >
                <strong>{snapshotDisplayName(snapshot)}</strong>
                <time>
                  {new Date(snapshot.created_at).toLocaleString('zh-CN')}
                </time>
                <small>导入快照 · {snapshot.summary.accepted} 个文件</small>
              </button>
            </li>
          ))}
        </ol>
        {query.data && !query.data.count && (
          <p className="panel-empty">尚无导入快照。</p>
        )}
        {query.data?.count === 1 && (
          <p role="note" className="pending-note">
            当前项目只有一份快照，至少需要两份不同快照才能比较。请先导入第二份快照。
          </p>
        )}
        {query.data && (
          <PageControls page={page} {...query.data} onPage={setPage} />
        )}
        {children}
      </div>
    </section>
  );
}
