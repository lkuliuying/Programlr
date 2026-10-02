import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Job, SourceFile } from '../../shared/api/generated/schema';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { queryJobs } from '../jobs';
import { submitAnalysis } from './api/analysis-api';

export function AnalysisNavigator({
  snapshotId,
  files,
  analysisId,
  onJob,
  onAnalysis,
}: {
  snapshotId: string;
  files: SourceFile[];
  analysisId: string | null;
  onJob: (id: string) => void;
  onAnalysis: (id: string) => void;
}) {
  const [root, setRoot] = useState(''),
    [page, setPage] = useState(1);
  const history = useQuery({
    queryKey: ['jobs', 'history', snapshotId, page],
    queryFn: ({ signal }) => queryJobs(snapshotId, page, signal),
    refetchInterval: (query) =>
      query.state.data?.results.some((job) =>
        ['queued', 'running'].includes(job.status),
      )
        ? 2000
        : false,
  });
  const operation = useIdempotentOperation<string, Job>(
    `analysis.${snapshotId}`,
    (root) => root,
    (root, key, signal) => submitAnalysis(snapshotId, root, key, signal),
    (job) => onJob(job.id),
    onJob,
  );
  return (
    <section>
      <h3>静态分析</h3>
      <form
        className="workspace-form"
        onSubmit={(event) => {
          event.preventDefault();
          operation.start(root);
        }}
      >
        <label>
          根路由文件
          <select
            required
            value={root}
            onChange={(event) => setRoot(event.target.value)}
          >
            <option value="">显式选择根 URLconf</option>
            {files
              .filter((file) => file.file_path.endsWith('.py'))
              .map((file) => (
                <option key={file.id} value={file.file_path}>
                  {file.file_path}
                </option>
              ))}
          </select>
        </label>
        <Button htmlType="submit" loading={operation.isPending}>
          {operation.pending ? '恢复本次分析' : '提交分析'}
        </Button>
        {operation.pending && <small>请选择原根路由，恢复相同操作。</small>}
        <Feedback error={operation.error} />
      </form>
      <h3>分析历史</h3>
      <Feedback
        error={history.error}
        retry={() => {
          void history.refetch();
        }}
      />
      {history.isPending && <p role="status">加载历史…</p>}
      {history.data && (
        <>
          <ul className="workspace-nav">
            {history.data.results.map((job) => {
              const id = job.result_url?.match(
                /^\/api\/v1\/analyses\/([a-f0-9-]{36})\/$/,
              )?.[1];
              return (
                <li key={job.id}>
                  <button
                    aria-current={id && id === analysisId ? 'true' : undefined}
                    onClick={() => (id ? onAnalysis(id) : onJob(job.id))}
                  >
                    {new Date(job.created_at).toLocaleString()}
                    <small>
                      {
                        {
                          queued: '等待处理',
                          running: '处理中',
                          failed: '失败，查看或重试',
                          succeeded: '查看分析结果',
                        }[job.status]
                      }
                    </small>
                  </button>
                </li>
              );
            })}
          </ul>
          {!history.data.count && <p>暂无分析记录。</p>}
          <PageControls page={page} {...history.data} onPage={setPage} />
        </>
      )}
    </section>
  );
}
