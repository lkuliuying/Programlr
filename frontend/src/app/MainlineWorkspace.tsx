import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from 'antd';
import type { Job, SourceRef } from '../shared/api/generated/schema';
import { Feedback } from '../shared/components/Feedback';
import { ScrollPanel } from '../shared/components/ScrollPanel';
import { Icon } from '../shared/components/Icon';
import { useIdempotentOperation } from '../shared/hooks/useIdempotentOperation';
import {
  getProject,
  listFiles,
  SourceWorkspace,
  SnapshotNameForm,
  snapshotDisplayName,
} from '../features/projects';
import { MainlineProjects } from '../features/projects/MainlineProjects';
import {
  getPreparedSnapshot,
  getSourceScan,
  scanSnapshot,
} from '../features/projects/api/mainline-api';
import { getAnalysis, AnalysisBrowser } from '../features/analysis';
import { submitAnalysis } from '../features/analysis/api/analysis-api';
import { ExplanationPanel } from '../features/explanations';
import { getJob } from '../features/jobs';
import { MainlineTask } from '../features/jobs/MainlineTask';
import { OperationLogs } from '../features/jobs/OperationLogs';
import { SnapshotKnowledge } from '../features/learning/SnapshotKnowledge';
import { RelationsPanel } from '../features/analysis/RelationsPanel';
import { WorkspaceShell } from './WorkspaceShell';
import {
  resolveWorkspaceSection,
  useWorkspaceLocation,
  type WorkspaceSection,
} from './workspace-location';
import './workspace.css';
import './pagination.css';
import './module-redesign.css';
import './shell-redesign.css';
import './mainline.css';

const retired = new Set<WorkspaceSection>([
  'comparison',
  'impact',
  'labs',
  'system',
]);
const preparationLabels = {
  pending: '等待源码识别',
  scanning: '正在识别源码与知识',
  needs_root: '请选择根路由',
  no_root: '没有可静态确定的根路由',
  analyzing: '正在分析接口',
  ready: '自动识别完成',
  failed: '识别未完成，可显式重试',
};

export function MainlineWorkspace() {
  const { selection, navigate, view } = useWorkspaceLocation();
  const section = resolveWorkspaceSection(selection, view);
  const legacy =
    retired.has(section) ||
    !!(
      selection.course ||
      selection.curriculum ||
      selection.goal ||
      selection.attempt ||
      selection.run ||
      selection.system_run ||
      selection.comparison
    );
  const management = section === 'workbench' || section === 'import';
  const logs = section === 'jobs';
  const workspace = !management && !logs && !legacy;
  const cache = useQueryClient();
  const followedJobs = useRef(new Set<string>());
  const closedSources = useRef(new Set<string>());
  const project = useQuery({
    queryKey: ['projects', 'detail', selection.project],
    queryFn: ({ signal }) => getProject(selection.project!, signal),
    enabled: !selection.invalid && !!selection.project,
  });
  const snapshot = useQuery({
    queryKey: ['projects', 'snapshot', selection.project, selection.snapshot],
    queryFn: ({ signal }) =>
      getPreparedSnapshot(selection.snapshot!, selection.project!, signal),
    enabled: !!project.data && !!selection.snapshot,
    refetchInterval: (query) =>
      query.state.data &&
      ['pending', 'scanning', 'analyzing'].includes(
        query.state.data.preparation_status,
      )
        ? 1500
        : false,
  });
  const files = useQuery({
    queryKey: ['projects', 'files', selection.snapshot],
    queryFn: ({ signal }) => listFiles(selection.snapshot!, signal),
    enabled: !!snapshot.data,
  });
  const analysisId = selection.analysis ?? snapshot.data?.analysis_id ?? null;
  const analysis = useQuery({
    queryKey: ['analysis', selection.snapshot, analysisId],
    queryFn: ({ signal }) =>
      getAnalysis(selection.snapshot!, analysisId!, signal),
    enabled: !!snapshot.data && !!analysisId,
    retry: false,
  });
  const scan = useQuery({
    queryKey: [
      'source-scans',
      selection.snapshot,
      snapshot.data?.source_scan_id,
    ],
    queryFn: ({ signal }) =>
      getSourceScan(
        snapshot.data!.source_scan_id!,
        selection.snapshot!,
        signal,
      ),
    enabled: !!snapshot.data?.source_scan_id,
  });
  const currentJob = useQuery({
    queryKey: ['jobs', 'detail', selection.job],
    queryFn: ({ signal }) => getJob(selection.job!, signal),
    enabled: !selection.invalid && !!selection.job,
    refetchInterval: (query) =>
      query.state.data &&
      ['queued', 'running'].includes(query.state.data.status)
        ? 1500
        : false,
  });
  useEffect(() => {
    const job = currentJob.data;
    if (!job || job.status !== 'succeeded' || followedJobs.current.has(job.id))
      return;
    followedJobs.current.add(job.id);
    if (String(job.kind) === 'delete') {
      void cache.cancelQueries({
        predicate: (query) =>
          query.queryKey[0] !== 'jobs' &&
          query.queryKey[0] !== 'operation-logs',
      });
      cache.removeQueries({
        predicate: (query) =>
          query.queryKey[0] !== 'jobs' &&
          query.queryKey[0] !== 'operation-logs',
      });
      navigate({ section: 'jobs', job: job.id });
    } else if (
      job.kind === 'import' &&
      job.snapshot_id &&
      selection.snapshot !== job.snapshot_id
    ) {
      navigate({
        project: selection.project,
        snapshot: job.snapshot_id,
        section: 'source',
      });
    }
  }, [currentJob.data, cache, navigate, selection.project, selection.snapshot]);
  useEffect(() => {
    if (snapshot.data?.analysis_id && !selection.analysis && workspace)
      navigate({ ...selection, analysis: snapshot.data.analysis_id });
  }, [snapshot.data?.analysis_id, selection, workspace, navigate]);
  useEffect(() => {
    if (
      !workspace ||
      selection.reference ||
      !analysis.data ||
      !files.data ||
      closedSources.current.has(selection.snapshot ?? '')
    )
      return;
    const root = files.data.find(
      (file) => file.file_path === analysis.data.root_urlconf,
    );
    if (root)
      navigate({
        ...selection,
        analysis: analysisId,
        reference: {
          snapshot_id: root.snapshot_id,
          file_path: root.file_path,
          start_line: 1,
          end_line: Math.max(1, root.line_count),
        },
      });
  }, [workspace, selection, analysis.data, files.data, analysisId, navigate]);
  const onSource = (reference: SourceRef) =>
    navigate({
      ...selection,
      analysis: analysisId,
      reference,
      section: 'source',
    });
  const onJob = (job: Job) => {
    void cache.invalidateQueries({ queryKey: ['projects', 'snapshot'] });
    navigate({ ...selection, job: job.id });
  };
  const scanOperation = useIdempotentOperation<string, Job>(
    `scan.${selection.snapshot}`,
    (id) => id,
    (id, key, signal) => scanSnapshot(id, key, signal),
    onJob,
  );
  const rootOperation = useIdempotentOperation<string, Job>(
    `root.${selection.snapshot}`,
    (path) => path,
    (path, key, signal) =>
      submitAnalysis(selection.snapshot!, path, key, signal),
    onJob,
  );
  const selected =
    selection.snapshot && analysisId && selection.endpoint !== null
      ? {
          snapshot: selection.snapshot,
          analysis: analysisId,
          endpoint: selection.endpoint,
        }
      : null;
  const pane = ['api', 'graph', 'learning', 'explanation'].includes(section)
    ? section
    : 'api';
  const ready = !!snapshot.data && !!files.data;
  return (
    <WorkspaceShell
      section={section}
      onSection={(next) => navigate({ ...selection, section: next })}
    >
      {selection.invalid ? (
        <section className="surface">
          <h1>工作区地址无效</h1>
          <p role="alert">选择参数缺失、重复或格式错误。</p>
          <a href="/">返回项目管理</a>
        </section>
      ) : (
        <>
          {legacy && (
            <section className="surface retired-feature">
              <h1>此功能已退役</h1>
              <p>
                课程、练习、实验、快照对比、候选影响及人工关系校准已从当前工作流移除。历史结果可通过操作日志中的任务详情读取。
              </p>
              <Button
                onClick={() =>
                  navigate({ section: 'jobs', job: selection.job })
                }
              >
                打开操作日志
              </Button>
            </section>
          )}
          <Feedback
            error={project.error ?? snapshot.error ?? files.error}
            retry={() => {
              void project.refetch();
              if (selection.snapshot) void snapshot.refetch();
            }}
          />
          {selection.job && !logs && (
            <MainlineTask
              id={selection.job}
              onJob={(job) => navigate({ ...selection, job: job.id })}
              onResult={(job) => {
                const match = /^\/api\/v1\/analyses\/([0-9a-f-]{36})\/$/.exec(
                  job.result_url ?? '',
                );
                if (match)
                  navigate({
                    ...selection,
                    analysis: match[1],
                    section: 'api',
                    job: null,
                  });
              }}
            />
          )}
          <div hidden={!management} className="mainline-page">
            <ScrollPanel active={management} label="项目管理">
              <header className="mainline-page-header management-heading">
                <span className="page-symbol">
                  <Icon name="folder" />
                </span>
                <div>
                  <p className="eyebrow">从源码出发，理解项目与知识</p>
                  <h1>项目管理</h1>
                  <p>上传源码后，系统自动识别接口、关系与知识点。</p>
                </div>
              </header>
              <MainlineProjects
                active={management}
                onOpenSnapshot={(project, snapshot) =>
                  navigate({ project, snapshot, section: 'source' })
                }
                onLogs={() => navigate({ ...selection, section: 'jobs' })}
                projectId={selection.project}
                snapshotId={selection.snapshot}
                project={project.data ?? null}
                onProject={(id) => navigate({ project: id, section: 'import' })}
                onSnapshot={(id) =>
                  navigate({
                    project: selection.project,
                    snapshot: id,
                    section: 'source',
                  })
                }
                onSubmitted={(id, job) =>
                  navigate({ project: id, job: job.id, section: 'import' })
                }
                onDelete={(job) =>
                  navigate({ ...selection, job: job.id, section: 'jobs' })
                }
              />
            </ScrollPanel>
          </div>
          {workspace && !ready && (
            <section className="surface">
              <h1>项目工作区</h1>
              <p>
                {selection.snapshot
                  ? '正在读取源码快照…'
                  : '先导入源码，或在项目管理中打开一个快照。'}
              </p>
              <Button
                onClick={() => navigate({ ...selection, section: 'import' })}
              >
                打开项目管理
              </Button>
            </section>
          )}
          {ready && (
            <section
              hidden={!workspace}
              className="mainline-workspace"
              data-tab={section}
            >
              <header className="mainline-page-header">
                {section === 'source' ? (
                  <h1 title={project.data?.name}>{project.data?.name}</h1>
                ) : (
                  <>
                    <div>
                      <p className="eyebrow">
                        {project.data?.name} /{' '}
                        {snapshotDisplayName(snapshot.data!)}
                      </p>
                      <h1>
                        {{
                          api: '接口',
                          graph: '关系',
                          learning: '知识',
                          explanation: '讲解',
                        }[section as 'api'] ?? '项目工作区'}
                      </h1>
                      <p role="status">
                        {preparationLabels[snapshot.data!.preparation_status]} ·{' '}
                        {snapshot.data!.summary.accepted} 个文件
                      </p>
                    </div>
                    <SnapshotNameForm snapshot={snapshot.data!} />
                  </>
                )}
              </header>
              <section className="preparation-status surface">
                {!!scan.data?.diagnostics?.length && (
                  <details>
                    <summary>
                      根路由识别诊断（{scan.data.diagnostics.length}）
                    </summary>
                    {scan.data.diagnostics.map((diagnostic, index) => (
                      <p key={index}>
                        {diagnostic.message}
                        {diagnostic.source_ref && (
                          <button
                            onClick={() => onSource(diagnostic.source_ref!)}
                          >
                            {diagnostic.source_ref.file_path}:
                            {diagnostic.source_ref.start_line}
                          </button>
                        )}
                      </p>
                    ))}
                  </details>
                )}
                {snapshot.data!.preparation_status === 'needs_root' && (
                  <>
                    <h2>根路由有多个候选</h2>
                    <p>
                      请选择本次分析的项目入口。知识识别已完成，可直接阅读。
                    </p>
                    <Feedback error={scan.error ?? rootOperation.error} />
                    {scan.data?.root_candidates.map((root) => (
                      <div className="root-candidate" key={root.file_path}>
                        <code>{root.file_path}</code>
                        <span>
                          {{
                            literal_root_urlconf: 'Django 字面量配置指定',
                            static_urlpatterns: '静态根路由候选',
                          }[root.reason] ?? root.reason}
                        </span>
                        {root.source_refs.map((reference, index) => (
                          <button
                            key={index}
                            onClick={() => onSource(reference)}
                          >
                            依据 {reference.file_path}:{reference.start_line}
                          </button>
                        ))}
                        <Button
                          loading={rootOperation.isPending}
                          onClick={() => rootOperation.start(root.file_path)}
                        >
                          选择此根路由
                        </Button>
                      </div>
                    ))}
                  </>
                )}
                {snapshot.data!.preparation_status === 'no_root' && (
                  <p>
                    当前规则未发现可静态确定的 Django
                    根路由。源码和知识仍可阅读；动态路由或其他框架的接口识别暂不支持。
                  </p>
                )}
                {['failed', 'pending'].includes(
                  snapshot.data!.preparation_status,
                ) && (
                  <>
                    <Button
                      loading={scanOperation.isPending}
                      onClick={() => scanOperation.start(selection.snapshot!)}
                    >
                      重新识别源码
                    </Button>
                    <Feedback error={scanOperation.error} />
                  </>
                )}
                {snapshot.data!.scan_job_id &&
                  ['scanning', 'failed'].includes(
                    snapshot.data!.preparation_status,
                  ) && (
                    <MainlineTask
                      id={snapshot.data!.scan_job_id}
                      onJob={onJob}
                    />
                  )}
                {snapshot.data!.analysis_job_id &&
                  ['analyzing', 'failed'].includes(
                    snapshot.data!.preparation_status,
                  ) && (
                    <MainlineTask
                      id={snapshot.data!.analysis_job_id}
                      onJob={onJob}
                    />
                  )}
              </section>
              <nav className="mainline-tabs" aria-label="工作区面板">
                {(
                  [
                    ['source', '源码'],
                    ['api', '接口'],
                    ['graph', '关系'],
                    ['learning', '知识'],
                    ['explanation', '讲解'],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    aria-current={section === key ? 'page' : undefined}
                    onClick={() =>
                      navigate({
                        ...selection,
                        analysis: analysisId,
                        section: key,
                      })
                    }
                  >
                    <Icon name={key} />
                    <span>{label}</span>
                  </button>
                ))}
              </nav>
              <div className="mainline-linked-panes">
                <div className="mainline-source-pane">
                  <SourceWorkspace
                    key={selection.snapshot}
                    analysisId={analysisId}
                    scanId={snapshot.data!.source_scan_id}
                    onExplain={() =>
                      navigate({
                        ...selection,
                        analysis: analysisId,
                        section: 'explanation',
                      })
                    }
                    onCloseSource={(
                      replacement = null,
                      closeSecondary = false,
                    ) => {
                      if (!replacement)
                        closedSources.current.add(selection.snapshot!);
                      navigate({
                        ...selection,
                        reference: replacement,
                        ...(closeSecondary ? { secondaryReference: null } : {}),
                      });
                    }}
                    files={files.data!}
                    snapshotId={selection.snapshot!}
                    snapshotName={snapshotDisplayName(snapshot.data!)}
                    reference={selection.reference}
                    secondaryReference={selection.secondaryReference}
                    onSource={onSource}
                    onSecondary={(secondaryReference) =>
                      navigate({ ...selection, secondaryReference })
                    }
                  />
                </div>
                <div className="mainline-detail-pane">
                  <div hidden={pane !== 'api'}>
                    <ScrollPanel
                      active={workspace && pane === 'api'}
                      label="接口分析"
                      resetKey={`${analysisId}:${selection.endpoint}`}
                    >
                      <Feedback error={analysis.error} />
                      {analysisId ? (
                        <AnalysisBrowser
                          snapshotId={selection.snapshot!}
                          analysisId={analysisId}
                          endpoint={selection.endpoint}
                          nodeId={selection.node}
                          onEndpoint={(endpoint) =>
                            navigate({
                              ...selection,
                              analysis: analysisId,
                              endpoint,
                              preview: null,
                              explanation: null,
                              job: null,
                            })
                          }
                          onNode={(node) =>
                            navigate({ ...selection, node: node.id })
                          }
                          onSource={onSource}
                        />
                      ) : (
                        <p>接口分析尚未完成。可以先阅读源码与知识。</p>
                      )}
                    </ScrollPanel>
                  </div>
                  <div hidden={pane !== 'graph'}>
                    <ScrollPanel
                      active={workspace && pane === 'graph'}
                      label="接口关系"
                      resetKey={analysisId ?? ''}
                    >
                      <RelationsPanel
                        selected={
                          analysisId
                            ? {
                                snapshot: selection.snapshot!,
                                analysis: analysisId,
                                endpoint: selection.endpoint,
                              }
                            : null
                        }
                        node={selection.node}
                        onNode={(node) =>
                          navigate({
                            ...selection,
                            node: node.id,
                            endpoint:
                              node.endpoint?.index ?? selection.endpoint,
                            preview: null,
                            explanation: null,
                            job: null,
                          })
                        }
                        onSource={onSource}
                      />
                    </ScrollPanel>
                  </div>
                  <div hidden={pane !== 'learning'}>
                    <ScrollPanel
                      active={workspace && pane === 'learning'}
                      label="源码知识"
                      resetKey={`${selection.snapshot}:${selection.reference?.file_path}:${selection.endpoint}`}
                    >
                      <SnapshotKnowledge
                        snapshotId={selection.snapshot!}
                        scanId={snapshot.data!.source_scan_id}
                        filePath={selection.reference?.file_path ?? null}
                        analysisId={analysisId}
                        endpoint={selection.endpoint}
                        onSource={onSource}
                        onRescan={() =>
                          scanOperation.start(selection.snapshot!)
                        }
                      />
                    </ScrollPanel>
                  </div>
                  <div hidden={pane !== 'explanation'}>
                    <ScrollPanel
                      active={workspace && pane === 'explanation'}
                      label="模型讲解"
                      resetKey={`${analysisId}:${selection.endpoint}`}
                    >
                      {selected ? (
                        <ExplanationPanel
                          key={`${selected.analysis}:${selected.endpoint}`}
                          selected={selected}
                          previewId={selection.preview}
                          explanationId={selection.explanation}
                          jobId={selection.job}
                          onSelect={(next) =>
                            navigate({
                              ...selection,
                              ...next,
                              analysis: analysisId,
                            })
                          }
                          onSource={onSource}
                        />
                      ) : (
                        <p>
                          先选择一个已识别的接口，再准备本次讲解的外发预览。
                        </p>
                      )}
                    </ScrollPanel>
                  </div>
                </div>
              </div>
            </section>
          )}
          <div hidden={!logs} className="mainline-page">
            <OperationLogs
              active={logs}
              jobId={selection.job}
              onJob={(job) =>
                navigate({ ...selection, job: job.id, section: 'jobs' })
              }
            />
          </div>
        </>
      )}
    </WorkspaceShell>
  );
}
