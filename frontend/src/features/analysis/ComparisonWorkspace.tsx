import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Tag } from 'antd';
import type {
  ComparisonFile,
  ComparisonInputRequest,
  Evidence,
  Job,
  SnapshotComparison,
  SourceRef,
} from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import {
  RecordList,
  type RecordColumn,
} from '../../shared/components/RecordList';
import { useIdempotentOperation } from '../../shared/hooks/useIdempotentOperation';
import {
  getSnapshot,
  listFiles,
  listSnapshots,
  snapshotDisplayName,
  SourceViewer,
} from '../projects';
import { queryJobs } from '../jobs';
import { ComparisonImpactPanel } from './ImpactPanel';
import {
  getComparison,
  getComparisonFile,
  listComparisonFiles,
  listComparisons,
  parseComparisonInput,
  submitComparison,
} from './api/comparison-api';

export const changeLabels = {
  added: '新增',
  deleted: '删除',
  modified: '修改',
  unchanged: '未变',
  ambiguous: '待判断',
};
type Input = Required<ComparisonInputRequest>;
export function ComparisonWorkspace({
  projectId,
  snapshotId,
  comparisonId,
  changeId,
  candidates,
  onCandidates,
  onComparison,
  onChange,
  onJob,
  onSource,
  onExplanation,
}: {
  projectId: string;
  snapshotId: string | null;
  comparisonId: string | null;
  changeId: string | null;
  candidates: boolean;
  onCandidates: (value: boolean) => void;
  onComparison: (id: string) => void;
  onChange: (id: string) => void;
  onJob: (id: string) => void;
  onSource: (ref: SourceRef, analysis: string | null) => void;
  onExplanation: (
    comparison: SnapshotComparison,
    id: string,
    analysis: string,
    endpoint: number,
  ) => void;
}) {
  const [page, setPage] = useState(1);
  const history = useQuery({
    queryKey: ['comparisons', 'history', projectId, page],
    queryFn: ({ signal }) => listComparisons(projectId, page, signal),
    refetchInterval: (q) =>
      q.state.data?.results.some((x) =>
        ['queued', 'running'].includes(x.job_status),
      )
        ? 2000
        : false,
  });
  return (
    <section className="comparison-workspace" aria-label="快照对比">
      <h2>快照对比</h2>
      <details open={!comparisonId}>
        <summary>创建对比与查看历史</summary>
        <ComparisonForm
          key={projectId}
          project={projectId}
          target={snapshotId}
          onJob={onJob}
        />
        <Feedback
          error={history.error}
          retry={() => {
            void history.refetch();
          }}
        />
        {history.isPending && <p role="status">读取对比历史…</p>}
        <ul className="workspace-nav">
          {history.data?.results.map((x) => (
            <li key={x.id}>
              <button
                type="button"
                aria-current={x.id === comparisonId ? 'true' : undefined}
                onClick={() =>
                  x.job_status === 'succeeded'
                    ? onComparison(x.id)
                    : onJob(x.job_id)
                }
              >
                {new Date(x.created_at).toLocaleString()} ·{' '}
                <SnapshotLabel project={projectId} id={x.base_snapshot_id} /> →{' '}
                <SnapshotLabel project={projectId} id={x.target_snapshot_id} />{' '}
                ·{' '}
                {
                  {
                    succeeded: '查看对比',
                    failed: '失败，可重试',
                    queued: '等待处理',
                    running: '处理中',
                  }[x.job_status]
                }
              </button>
            </li>
          ))}
        </ul>
        {history.data && (
          <PageControls page={page} {...history.data} onPage={setPage} />
        )}
      </details>
      {comparisonId && (
        <ComparisonResult
          key={comparisonId}
          project={projectId}
          id={comparisonId}
          changeId={changeId}
          candidates={candidates}
          onCandidates={onCandidates}
          onChange={onChange}
          onSource={onSource}
          onExplanation={onExplanation}
        />
      )}
    </section>
  );
}
function ComparisonForm({
  project,
  target,
  onJob,
}: {
  project: string;
  target: string | null;
  onJob: (id: string) => void;
}) {
  const storage = `learning-lab.comparison-input.${project}`;
  const [initial] = useState(() => {
    try {
      const saved = sessionStorage.getItem(storage);
      return {
        input: saved ? parseComparisonInput(JSON.parse(saved)) : null,
        error: null,
      };
    } catch {
      return {
        input: null,
        error: new Error('恢复输入损坏，请先核对对比历史；不会替换未知提交。'),
      };
    }
  });
  const [base, setBase] = useState(initial.input?.base_snapshot_id ?? ''),
    [next, setNext] = useState(
      initial.input?.target_snapshot_id ?? target ?? '',
    ),
    [baseAnalysis, setBaseAnalysis] = useState<string | null>(
      initial.input?.base_analysis_id ?? null,
    ),
    [nextAnalysis, setNextAnalysis] = useState<string | null>(
      initial.input?.target_analysis_id ?? null,
    );
  const operation = useIdempotentOperation<Input, Job>(
    `comparison.${project}`,
    (input) => JSON.stringify(input),
    (input, key, signal) => submitComparison(project, input, key, signal),
    (job) => {
      sessionStorage.removeItem(storage);
      onJob(job.id);
    },
    onJob,
    (_, retained) => {
      if (!retained) sessionStorage.removeItem(storage);
    },
  );
  return (
    <form
      className="workspace-form"
      onSubmit={(event) => {
        event.preventDefault();
        const input = {
          base_snapshot_id: base,
          target_snapshot_id: next,
          base_analysis_id: baseAnalysis,
          target_analysis_id: nextAnalysis,
        };
        if (initial.error) return;
        sessionStorage.setItem(storage, JSON.stringify(input));
        operation.start(input);
      }}
    >
      <p>
        显式选择两侧快照；同时选择分析时比较接口和关系。原有分析与讲解保持原快照。
      </p>
      <SnapshotPicker
        project={project}
        label="基准"
        selected={base}
        analysis={baseAnalysis}
        disabled={operation.pending || operation.isPending || !!initial.error}
        onSnapshot={(id) => {
          setBase(id);
          setBaseAnalysis(null);
        }}
        onAnalysis={setBaseAnalysis}
      />
      <SnapshotPicker
        project={project}
        label="目标"
        selected={next}
        analysis={nextAnalysis}
        disabled={operation.pending || operation.isPending || !!initial.error}
        onSnapshot={(id) => {
          setNext(id);
          setNextAnalysis(null);
        }}
        onAnalysis={setNextAnalysis}
      />
      <Button
        htmlType="submit"
        disabled={
          !base ||
          !next ||
          (baseAnalysis === null) !== (nextAnalysis === null) ||
          !!initial.error
        }
        loading={operation.isPending}
      >
        {operation.pending ? '恢复本次对比提交' : '提交快照对比'}
      </Button>
      {operation.pending && (
        <p>保留原绑定和操作标识；请核对历史或恢复同一次提交。</p>
      )}
      <Feedback error={initial.error ?? operation.error} />
    </form>
  );
}
function SnapshotPicker({
  project,
  label,
  selected,
  analysis,
  disabled,
  onSnapshot,
  onAnalysis,
}: {
  project: string;
  label: string;
  selected: string;
  analysis: string | null;
  disabled: boolean;
  onSnapshot: (id: string) => void;
  onAnalysis: (id: string | null) => void;
}) {
  const [page, setPage] = useState(1),
    [analysisPage, setAnalysisPage] = useState(1);
  const snapshots = useQuery({
    queryKey: ['projects', 'snapshots', project, page],
    queryFn: ({ signal }) => listSnapshots(project, page, signal),
  });
  const selectedSnapshot = useQuery({
    queryKey: ['projects', 'snapshot', project, selected],
    queryFn: ({ signal }) => getSnapshot(selected, project, signal),
    enabled:
      !!selected &&
      !!snapshots.data &&
      !snapshots.data.results.some((x) => x.id === selected),
  });
  const jobs = useQuery({
    queryKey: ['jobs', 'history', selected, analysisPage],
    queryFn: ({ signal }) => queryJobs(selected, analysisPage, signal),
    enabled: !!selected,
  });
  const analyses =
    jobs.data?.results.flatMap((job) => {
      const id =
        job.status === 'succeeded'
          ? job.result_url?.match(
              /^\/api\/v1\/analyses\/([a-f0-9-]{36})\/$/,
            )?.[1]
          : null;
      return id ? [{ id, created: job.created_at }] : [];
    }) ?? [];
  return (
    <fieldset disabled={disabled}>
      <legend>{label}快照与分析</legend>
      <label>
        {label}快照
        <select
          required
          value={selected}
          onChange={(e) => {
            onSnapshot(e.target.value);
            setAnalysisPage(1);
          }}
        >
          <option value="">选择快照</option>
          {selected &&
            !snapshots.data?.results.some((x) => x.id === selected) && (
              <option value={selected}>
                {selectedSnapshot.data
                  ? snapshotDisplayName(selectedSnapshot.data)
                  : selectedSnapshot.error
                    ? '所选快照信息不可用'
                    : '读取所选快照名称…'}
              </option>
            )}
          {snapshots.data?.results.map((x) => (
            <option key={x.id} value={x.id}>
              {snapshotDisplayName(x)}
            </option>
          ))}
        </select>
      </label>
      <Feedback error={snapshots.error} />
      <Feedback error={selectedSnapshot.error} />
      {snapshots.data && (
        <PageControls page={page} {...snapshots.data} onPage={setPage} />
      )}
      {selected && (
        <>
          <label>
            {label}分析
            <select
              value={analysis ?? ''}
              onChange={(e) => onAnalysis(e.target.value || null)}
            >
              <option value="">不指定分析（两侧仅文件）</option>
              {analysis && !analyses.some((x) => x.id === analysis) && (
                <option value={analysis}>已选 {analysis}</option>
              )}
              {analyses.map((x) => (
                <option key={x.id} value={x.id}>
                  {new Date(x.created).toLocaleString()} · {x.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          <Feedback error={jobs.error} />
          {jobs.data && (
            <PageControls
              page={analysisPage}
              {...jobs.data}
              onPage={setAnalysisPage}
            />
          )}
        </>
      )}
    </fieldset>
  );
}
function ComparisonResult({
  project,
  id,
  changeId,
  candidates,
  onCandidates,
  onChange,
  onSource,
  onExplanation,
}: {
  project: string;
  id: string;
  changeId: string | null;
  candidates: boolean;
  onCandidates: (value: boolean) => void;
  onChange: (id: string) => void;
  onSource: (ref: SourceRef, analysis: string | null) => void;
  onExplanation: (
    comparison: SnapshotComparison,
    id: string,
    analysis: string,
    endpoint: number,
  ) => void;
}) {
  const query = useQuery({
    queryKey: ['comparisons', 'detail', project, id],
    queryFn: ({ signal }) => getComparison(id, project, signal),
  });
  return (
    <>
      <Feedback
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {query.isPending && <p role="status">读取对比结果…</p>}
      {query.data && (
        <ComparisonDetails
          data={query.data}
          changeId={changeId}
          onChange={onChange}
          onSource={onSource}
          onExplanation={onExplanation}
        />
      )}
      {query.data && (
        <ComparisonImpactPanel
          comparison={query.data}
          change={changeId}
          candidates={candidates}
          onCandidates={onCandidates}
          onSource={onSource}
        />
      )}
    </>
  );
}
function EvidenceLinks({
  evidence,
  analysis,
  onSource,
}: {
  evidence: Evidence[];
  analysis: string | null;
  onSource: (ref: SourceRef, analysis: string | null) => void;
}) {
  return (
    <ul>
      {evidence.map((x, i) => (
        <li key={i}>
          {x.rule}
          {x.source_ref && (
            <button
              type="button"
              onClick={() => onSource(x.source_ref!, analysis)}
            >
              {x.source_ref.file_path}:{x.source_ref.start_line}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
function ComparisonDetails({
  data,
  changeId,
  onChange,
  onSource,
  onExplanation,
}: {
  data: SnapshotComparison;
  changeId: string | null;
  onChange: (id: string) => void;
  onSource: (ref: SourceRef, analysis: string | null) => void;
  onExplanation: (
    comparison: SnapshotComparison,
    id: string,
    analysis: string,
    endpoint: number,
  ) => void;
}) {
  const [page, setPage] = useState(1),
    [showUnchanged, setShowUnchanged] = useState(false),
    [interfacePage, setInterfacePage] = useState(1),
    [relationPage, setRelationPage] = useState(1);
  const files = useQuery({
    queryKey: ['comparisons', 'files', data.id, page],
    queryFn: ({ signal }) => listComparisonFiles(data, page, signal),
  });
  const interfaces = data.interfaces.filter(
      (x) => showUnchanged || x.change_type !== 'unchanged',
    ),
    relations = data.relations.filter(
      (x) => showUnchanged || x.change_type !== 'unchanged',
    );
  const fileTitle = (file: ComparisonFile) => (
    <button
      type="button"
      className="record-choice"
      aria-label={`${changeLabels[file.change_type]} · ${file.file_path}`}
      aria-current={changeId === file.id ? 'true' : undefined}
      onClick={() => onChange(file.id)}
    >
      <code>{file.file_path}</code>
    </button>
  );
  const fileColumns: RecordColumn<ComparisonFile>[] = [
    { key: 'path', title: '文件路径', render: fileTitle },
    {
      key: 'change',
      title: '变化类型',
      width: 120,
      render: (file) => <Tag>{changeLabels[file.change_type]}</Tag>,
    },
  ];
  return (
    <>
      <p>
        基准{' '}
        <SnapshotLabel project={data.project_id} id={data.base_snapshot_id} /> →
        目标{' '}
        <SnapshotLabel project={data.project_id} id={data.target_snapshot_id} />
      </p>
      <p>
        {Object.entries(data.summary).map(([key, count]) => (
          <Tag key={key}>
            {changeLabels[key as keyof typeof data.summary]} {count}
          </Tag>
        ))}
      </p>
      {data.comparison_notes.map((note, i) => (
        <p key={i}>{note}</p>
      ))}
      <details>
        <summary>两侧规则与分析版本</summary>
        <pre>
          {JSON.stringify(
            { 基准: data.base_version, 目标: data.target_version },
            null,
            2,
          )}
        </pre>
      </details>
      <h3>文件变化</h3>
      <Feedback
        error={files.error}
        retry={() => {
          void files.refetch();
        }}
      />
      {files.isPending && <p role="status">读取文件变化…</p>}
      {files.data && (
        <RecordList
          label="文件变化"
          records={files.data.results}
          columns={fileColumns}
          rowKey={(file) => file.id}
          recordTitle={fileTitle}
          titleColumnKey="path"
          selectedKey={changeId ?? undefined}
          empty={
            files.data.count
              ? '当前批次没有文件变化记录，请查看其他批次。'
              : '当前对比没有文件变化记录。'
          }
        />
      )}
      {files.data && (
        <PageControls page={page} {...files.data} onPage={setPage} />
      )}
      {changeId && (
        <FileDifference key={changeId} comparison={data} id={changeId} />
      )}
      {data.comparability === 'comparable' && (
        <>
          <label>
            <input
              type="checkbox"
              checked={showUnchanged}
              onChange={(e) => {
                setShowUnchanged(e.target.checked);
                setInterfacePage(1);
                setRelationPage(1);
              }}
            />
            包含未变接口和关系
          </label>
          <h3>接口变化（{interfaces.length}）</h3>
          {interfaces
            .slice((interfacePage - 1) * 20, interfacePage * 20)
            .map((x, i) => (
              <details key={i}>
                <summary>
                  {changeLabels[x.change_type]} · {x.method} {x.path} ·{' '}
                  {x.changed_fields.join('、')}
                </summary>
                <p>
                  基准接口 {x.base_indices.join(', ')}；目标接口{' '}
                  {x.target_indices.join(', ')}
                  。待判断项不能归因为确定的源码变化。
                </p>
                <h4>基准依据</h4>
                <EvidenceLinks
                  evidence={x.base_evidence}
                  analysis={data.base_analysis_id}
                  onSource={onSource}
                />
                <h4>目标依据</h4>
                <EvidenceLinks
                  evidence={x.target_evidence}
                  analysis={data.target_analysis_id}
                  onSource={onSource}
                />
              </details>
            ))}
          <PageControls
            page={interfacePage}
            next={interfacePage * 20 < interfaces.length ? 'next' : null}
            previous={interfacePage > 1 ? 'previous' : null}
            onPage={setInterfacePage}
          />
          <h3>关系变化（{relations.length}）</h3>
          {relations
            .slice((relationPage - 1) * 20, relationPage * 20)
            .map((x, i) => (
              <details key={i}>
                <summary>
                  {changeLabels[x.change_type]} · {x.source_name} →{' '}
                  {x.target_name} · {x.relation}
                </summary>
                <h4>基准依据</h4>
                <EvidenceLinks
                  evidence={x.base_evidence}
                  analysis={data.base_analysis_id}
                  onSource={onSource}
                />
                <h4>目标依据</h4>
                <EvidenceLinks
                  evidence={x.target_evidence}
                  analysis={data.target_analysis_id}
                  onSource={onSource}
                />
              </details>
            ))}
          <PageControls
            page={relationPage}
            next={relationPage * 20 < relations.length ? 'next' : null}
            previous={relationPage > 1 ? 'previous' : null}
            onPage={setRelationPage}
          />
        </>
      )}
      <h3>旧讲解引用适用性</h3>
      <p>引用文件未变不等于讲解语义已验证；打开旧讲解仍定位原快照。</p>
      {data.evidence.map((x) => (
        <details key={x.explanation_id}>
          <summary>讲解 {x.explanation_id.slice(0, 8)}</summary>
          <button
            type="button"
            onClick={() =>
              onExplanation(
                data,
                x.explanation_id,
                x.analysis_id,
                x.endpoint_index,
              )
            }
          >
            打开旧讲解
          </button>
          {x.warning && <p role="alert">{x.warning}</p>}
          <ul>
            {x.references.map((ref, i) => (
              <li key={i}>
                {
                  {
                    unchanged: '引用文件未变',
                    review: '需要复核',
                    deleted: '来源已删除',
                    unknown: '无法判断',
                  }[ref.applicability]
                }{' '}
                ·{' '}
                <button
                  type="button"
                  onClick={() => onSource(ref.source_ref, x.analysis_id)}
                >
                  {ref.source_ref.file_path}:{ref.source_ref.start_line}
                  （原引用）
                </button>
              </li>
            ))}
          </ul>
        </details>
      ))}
      {!data.evidence.length && <p>基准快照没有已保存的讲解引用。</p>}
    </>
  );
}

function SnapshotLabel({ project, id }: { project: string; id: string }) {
  const query = useQuery({
    queryKey: ['projects', 'snapshot', project, id],
    queryFn: ({ signal }) => getSnapshot(id, project, signal),
  });
  return (
    <span>
      {query.data
        ? snapshotDisplayName(query.data)
        : query.error
          ? '快照信息不可用'
          : '读取快照名称…'}
    </span>
  );
}
function FileDifference({
  comparison,
  id,
}: {
  comparison: SnapshotComparison;
  id: string;
}) {
  const query = useQuery({
    queryKey: ['comparisons', 'file', comparison.id, id],
    queryFn: ({ signal }) => getComparisonFile(comparison, id, signal),
  });
  const file = query.data;
  return (
    <section aria-label="行级差异">
      <Feedback
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {file && (
        <>
          <h4>{file.file_path}</h4>
          {file.diff ? (
            <pre className="source-diff">{file.diff}</pre>
          ) : (
            <p>文件内容未变。</p>
          )}
          <div className="comparison-sources">
            {file.base_ref && (
              <SnapshotSource
                project={comparison.project_id}
                snapshot={comparison.base_snapshot_id}
                reference={file.base_ranges[0] ?? file.base_ref}
                label="基准源码"
              />
            )}
            {file.target_ref && (
              <SnapshotSource
                project={comparison.project_id}
                snapshot={comparison.target_snapshot_id}
                reference={file.target_ranges[0] ?? file.target_ref}
                label="目标源码"
              />
            )}
          </div>
        </>
      )}
    </section>
  );
}
function SnapshotSource({
  project,
  snapshot,
  reference,
  label,
}: {
  project: string;
  snapshot: string;
  reference: SourceRef;
  label: string;
}) {
  const metadata = useQuery({
    queryKey: ['projects', 'snapshot', project, snapshot],
    queryFn: ({ signal }) => getSnapshot(snapshot, project, signal),
  });
  const files = useQuery({
    queryKey: ['projects', 'files', snapshot],
    queryFn: ({ signal }) => listFiles(snapshot, signal),
    enabled: !!metadata.data,
  });
  return (
    <div>
      <h4>{label}</h4>
      <Feedback error={metadata.error} />
      {metadata.isPending && <p role="status">读取快照名称…</p>}
      <Feedback error={files.error} />
      {files.data && metadata.data && (
        <SourceViewer
          snapshotId={snapshot}
          snapshotName={snapshotDisplayName(metadata.data)}
          reference={reference}
          files={files.data}
        />
      )}
    </div>
  );
}
