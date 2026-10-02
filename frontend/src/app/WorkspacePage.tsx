import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import type { ReactNode } from 'react';
import type {
  GraphNode,
  Job,
  SourceRef,
  SourceFile,
} from '../shared/api/generated/schema';
import { Feedback } from '../shared/components/Feedback';
import {
  ProjectNavigator,
  ImportForm,
  SourceWorkspace,
  SnapshotTimeline,
  SnapshotNameForm,
  snapshotDisplayName,
  getProject,
  getSnapshot,
  listFiles,
} from '../features/projects';
import {
  AnalysisBrowser,
  AnalysisNavigator,
  ComparisonWorkspace,
  StaticGraphPanel,
  CandidateImpactPanel,
} from '../features/analysis';
import { JobStatus, JobsPage, SystemStatusSummary } from '../features/jobs';
import { ExplanationPanel } from '../features/explanations';
import { LabPanel } from '../features/labs';
import { LearningPanel, KnowledgePanel } from '../features/learning';
import { WorkspaceShell } from './WorkspaceShell';
import {
  useWorkspaceLocation,
  type WorkspaceSelection,
  type WorkspaceSection,
  resolveWorkspaceSection,
} from './workspace-location';
import {
  WorkbenchPage,
  ImportPage,
  SourcePage,
  ApiPage,
  GraphPage,
  ComparisonPage,
  ImpactPage,
  KnowledgePage,
  PracticePage,
  ExplanationPage,
  SystemPage,
  ModuleRequirement,
} from './WorkspaceModulePages';
import './workspace.css';

type Navigate = (selection: Partial<WorkspaceSelection>) => void;
export function WorkspacePage() {
  const { selection, navigate, view } = useWorkspaceLocation();
  const [searchState, setSearch] = useState({
    snapshot: selection.snapshot,
    value: '',
  });
  const search =
    searchState.snapshot === selection.snapshot ? searchState.value : '';
  const section = resolveWorkspaceSection(selection, view);
  const onSection = (section: WorkspaceSection) =>
    navigate({ ...selection, section });
  return (
    <WorkspaceShell
      section={section}
      onSection={onSection}
      search={search}
      searchable={
        !!selection.snapshot && !selection.invalid && section !== 'jobs'
      }
      onSearch={(value) => setSearch({ snapshot: selection.snapshot, value })}
    >
      {selection.invalid ? (
        <section className="invalid-workspace surface">
          <h1>工作区地址无效</h1>
          <p role="alert">选择参数缺失、重复或格式错误，请重新进入工作区。</p>
          <a href="/">返回项目选择</a>
        </section>
      ) : (
        <WorkspaceContent
          key={selection.project ?? 'unselected'}
          selection={selection}
          navigate={navigate}
          section={section}
          search={search}
        />
      )}
    </WorkspaceShell>
  );
}
function WorkspaceContent({
  selection,
  navigate,
  section,
  search,
}: {
  selection: WorkspaceSelection;
  navigate: Navigate;
  section: WorkspaceSection;
  search: string;
}) {
  const onSection = (section: WorkspaceSection) =>
    navigate({ ...selection, section });
  const project = useQuery({
    queryKey: ['projects', 'detail', selection.project],
    queryFn: ({ signal }) => getProject(selection.project!, signal),
    enabled: !!selection.project,
  });
  const snapshot = useQuery({
    queryKey: ['projects', 'snapshot', selection.project, selection.snapshot],
    queryFn: ({ signal }) =>
      getSnapshot(selection.snapshot!, selection.project!, signal),
    enabled: !!project.data && !!selection.snapshot,
  });
  const files = useQuery({
    queryKey: ['projects', 'files', selection.project, selection.snapshot],
    queryFn: ({ signal }) => listFiles(selection.snapshot!, signal),
    enabled: !!snapshot.data,
  });
  const onJob = (job: string) =>
    navigate({ ...selection, job, section: 'jobs' });
  const onResult = (job: Job) => {
    if (job.kind === 'import' && job.snapshot_id)
      navigate({
        project: selection.project,
        snapshot: job.snapshot_id,
        section: 'workbench',
      });
    if (job.kind === 'analysis' && job.snapshot_id === selection.snapshot) {
      const analysis = job.result_url?.match(
        /^\/api\/v1\/analyses\/([a-f0-9-]{36})\/$/,
      )?.[1];
      if (analysis)
        navigate({
          project: selection.project,
          snapshot: selection.snapshot,
          analysis,
          section: 'api',
        });
    }
    if (job.kind === 'snapshot_comparison') {
      const comparison = job.result_url?.match(
        /^\/api\/v1\/snapshot-comparisons\/([a-f0-9-]{36})\/$/,
      )?.[1];
      if (comparison)
        navigate({
          ...selection,
          comparison,
          change: null,
          section: 'comparison',
        });
    }
    if (job.kind === 'lab') {
      const system_run = job.result_url?.match(
        /^\/api\/v1\/system-lab-runs\/([a-f0-9-]{36})\/$/,
      )?.[1];
      const run = job.result_url?.match(
        /^\/api\/v1\/lab-runs\/([a-f0-9-]{36})\/$/,
      )?.[1];
      if (system_run || run)
        navigate({
          ...selection,
          system_run: system_run ?? null,
          run: run ?? null,
          panel: 'lab',
          section: 'labs',
        });
    }
    if (
      job.kind === 'explanation' &&
      job.snapshot_id === selection.snapshot &&
      selection.endpoint !== null
    ) {
      const explanation = job.result_url?.match(
        /^\/api\/v1\/explanations\/([a-f0-9-]{36})\/$/,
      )?.[1];
      if (explanation)
        navigate({
          ...selection,
          explanation,
          panel: 'explanation',
          section: 'explanation',
        });
    }
  };
  const requirement = (
    purpose: string,
    needs: 'snapshot' | 'analysis' | 'endpoint' = 'snapshot',
  ) => {
    const unavailable = !!(project.error ?? snapshot.error ?? files.error);
    if (
      selection.project &&
      !unavailable &&
      (project.isPending || (selection.snapshot && !files.data))
    )
      return <p role="status">{purpose}：正在读取所需的项目与快照…</p>;
    const message = unavailable
      ? purpose + '所需的项目、快照或文件无法读取，请重新选择或重试。'
      : !selection.project
        ? purpose + '需要先打开一个项目。'
        : !selection.snapshot
          ? purpose + '需要先导入或选择一个快照。'
          : needs !== 'snapshot' && !selection.analysis
            ? purpose + '需要先在 API 分析中选择或提交分析。'
            : purpose + '需要先在 API 分析中选择一个接口。';
    const target: WorkspaceSection =
      unavailable || !selection.project || !selection.snapshot
        ? 'import'
        : 'api';
    return (
      <ModuleRequirement
        message={message}
        action={target === 'import' ? '前往项目导入' : '前往 API 分析'}
        onAction={() => onSection(target)}
      />
    );
  };
  const ready = !!snapshot.data && !!files.data;
  return (
    <>
      <Feedback
        error={project.error ?? snapshot.error ?? files.error}
        retry={() => {
          if (project.error) void project.refetch();
          else if (snapshot.error) void snapshot.refetch();
          else void files.refetch();
        }}
      />
      {selection.project &&
        (project.isPending ||
          (selection.snapshot && snapshot.isPending) ||
          (snapshot.data && files.isPending)) && (
          <p role="status">读取当前项目与快照…</p>
        )}
      {snapshot.data && (
        <div
          hidden={section !== 'import' && section !== 'comparison'}
          className="snapshot-name-toolbar"
        >
          <SnapshotNameForm key={snapshot.data.id} snapshot={snapshot.data} />
        </div>
      )}
      <WorkbenchPage
        active={section === 'workbench'}
        project={project.data}
        snapshot={snapshot.data}
        files={files.data}
        analysis={selection.analysis}
        loading={
          !!selection.project &&
          (project.isPending ||
            (!!selection.snapshot && snapshot.isPending) ||
            (!!snapshot.data && files.isPending))
        }
        unavailable={!!(project.error ?? snapshot.error ?? files.error)}
        onSection={onSection}
      />
      <ImportPage active={section === 'import'}>
        <div className="import-module-grid">
          <section className="surface module-summary">
            <ProjectNavigator
              projectId={selection.project}
              snapshotId={selection.snapshot}
              onProject={(project) => navigate({ project, section: 'import' })}
              onSnapshot={(snapshot) =>
                navigate({
                  project: selection.project,
                  snapshot,
                  section: 'workbench',
                })
              }
            />
          </section>
          <section className="surface module-summary">
            <h2>导入新快照</h2>
            {project.data ? (
              <ImportForm
                key={project.data.id}
                projectId={project.data.id}
                onJob={onJob}
              />
            ) : (
              <p>创建或打开项目后，选择源码 ZIP。</p>
            )}
            <h3>导入边界</h3>
            <ul>
              <li>只接收经过校验的源码文件。</li>
              <li>不安装依赖，不执行导入项目。</li>
              <li>快照只读，后续分析需显式提交。</li>
            </ul>
          </section>
        </div>
      </ImportPage>
      {!ready && (
        <>
          <SourcePage active={section === 'source'}>
            {requirement('源码阅读')}
          </SourcePage>
          <ApiPage active={section === 'api'}>
            {requirement('API 分析')}
          </ApiPage>
          <GraphPage active={section === 'graph'}>
            {requirement('静态关系图', 'analysis')}
          </GraphPage>
          <ImpactPage active={section === 'impact'}>
            {requirement('候选影响', 'analysis')}
          </ImpactPage>
          <ExplanationPage active={section === 'explanation'}>
            {requirement('模型讲解', 'endpoint')}
          </ExplanationPage>
          <PracticePage active={section === 'labs'}>
            {requirement('练习与实验', 'endpoint')}
          </PracticePage>
        </>
      )}
      {ready && (
        <SnapshotPages
          key={selection.snapshot}
          selection={selection}
          navigate={navigate}
          section={section}
          search={search}
          files={files.data!}
          snapshotName={snapshotDisplayName(snapshot.data!)}
          onJob={onJob}
          requirement={requirement}
        />
      )}
      <KnowledgePage active={section === 'learning'}>
        <KnowledgePanel
          key={
            selection.snapshot +
            '.' +
            selection.analysis +
            '.' +
            selection.endpoint
          }
          selected={
            ready && selection.analysis && selection.endpoint !== null
              ? {
                  snapshot: selection.snapshot!,
                  analysis: selection.analysis,
                  endpoint: selection.endpoint,
                }
              : null
          }
          curriculumId={selection.curriculum}
          goal={selection.goal ?? 'create-task'}
          onPath={(curriculum, goal) =>
            navigate({
              ...selection,
              curriculum,
              goal,
              panel: 'learning',
              section: 'learning',
            })
          }
        />
      </KnowledgePage>
      <ComparisonPage active={section === 'comparison'}>
        {project.data ? (
          <div className="comparison-module-grid">
            <SnapshotTimeline
              project={project.data.id}
              selected={selection.snapshot}
              onSelect={(snapshot) =>
                navigate({
                  project: selection.project,
                  snapshot,
                  section: 'comparison',
                })
              }
              onCompare={() => onSection('comparison')}
            />
            <ComparisonWorkspace
              projectId={project.data.id}
              snapshotId={selection.snapshot}
              comparisonId={selection.comparison}
              changeId={selection.change}
              candidates={selection.candidates}
              onCandidates={(candidates) =>
                navigate({ ...selection, candidates })
              }
              onComparison={(comparison) =>
                navigate({ ...selection, comparison, change: null })
              }
              onChange={(change) => navigate({ ...selection, change })}
              onJob={onJob}
              onSource={(reference, analysis) =>
                navigate({
                  project: selection.project,
                  snapshot: reference.snapshot_id,
                  analysis,
                  reference,
                  comparison: selection.comparison,
                  change: selection.change,
                  candidates: selection.candidates,
                  section: 'source',
                })
              }
              onExplanation={(comparison, explanation, analysis, endpoint) =>
                navigate({
                  project: selection.project,
                  snapshot: comparison.base_snapshot_id,
                  analysis,
                  endpoint,
                  explanation,
                  comparison: comparison.id,
                  change: selection.change,
                  candidates: selection.candidates,
                  section: 'explanation',
                })
              }
            />
          </div>
        ) : (
          requirement('快照与对比')
        )}
      </ComparisonPage>
      <SystemPage active={section === 'jobs'}>
        <SystemStatusSummary onOpen={() => onSection('jobs')} />
        {selection.job && (
          <JobStatus
            key={selection.job}
            id={selection.job}
            snapshotId={selection.snapshot}
            onSelect={onJob}
            onResult={onResult}
          />
        )}
        <JobsPage embedded active={section === 'jobs'} />
      </SystemPage>
    </>
  );
}
function SnapshotPages({
  selection,
  navigate,
  section,
  search,
  files,
  snapshotName,
  onJob,
  requirement,
}: {
  selection: WorkspaceSelection;
  navigate: Navigate;
  section: WorkspaceSection;
  search: string;
  files: SourceFile[];
  snapshotName: string;
  onJob: (job: string) => void;
  requirement: (
    purpose: string,
    needs?: 'snapshot' | 'analysis' | 'endpoint',
  ) => ReactNode;
}) {
  const snapshotId = selection.snapshot!;
  const selected =
    selection.analysis && selection.endpoint !== null
      ? {
          snapshot: snapshotId,
          analysis: selection.analysis,
          endpoint: selection.endpoint,
        }
      : null;
  const onSource = (reference: SourceRef) =>
    navigate({
      ...selection,
      reference,
      section: 'source',
      panel: selection.endpoint === null ? null : 'source',
    });
  const onNode = (node: GraphNode) =>
    navigate({
      ...selection,
      ...(node.endpoint !== null &&
      node.endpoint.index !== selection.endpoint &&
      !(section === 'graph' && selection.endpoint === null)
        ? {
            endpoint: node.endpoint.index,
            preview: null,
            explanation: null,
            attempt: null,
            run: null,
            system_run: null,
            curriculum: null,
            goal: null,
            panel: null,
            job: null,
          }
        : {}),
      node: node.id,
      section,
    });
  const labMode =
    selection.panel === 'lab' ||
    (selection.panel === null && !!(selection.run || selection.system_run));
  return (
    <>
      <SourcePage active={section === 'source'}>
        <SourceWorkspace
          files={files}
          snapshotId={snapshotId}
          snapshotName={snapshotName}
          reference={selection.reference}
          secondaryReference={selection.secondaryReference}
          search={search}
          onSource={onSource}
          onSecondary={(secondaryReference) =>
            navigate({ ...selection, secondaryReference })
          }
        />
      </SourcePage>
      <ApiPage active={section === 'api'}>
        <div className="api-module-grid">
          <aside className="surface module-summary">
            <AnalysisNavigator
              snapshotId={snapshotId}
              files={files}
              analysisId={selection.analysis}
              onJob={onJob}
              onAnalysis={(analysis) =>
                navigate({
                  project: selection.project,
                  snapshot: snapshotId,
                  analysis,
                  section: 'api',
                })
              }
            />
          </aside>
          <div>
            {selection.analysis ? (
              <AnalysisBrowser
                key={selection.analysis}
                snapshotId={snapshotId}
                analysisId={selection.analysis}
                endpoint={selection.endpoint}
                nodeId={selection.node}
                onEndpoint={(endpoint) =>
                  navigate({
                    ...selection,
                    endpoint,
                    node: null,
                    reference: null,
                    preview: null,
                    explanation: null,
                    attempt: null,
                    run: null,
                    system_run: null,
                    curriculum: null,
                    goal: null,
                    panel: null,
                    job: null,
                    section: 'api',
                  })
                }
                onNode={onNode}
                onSource={onSource}
              />
            ) : (
              requirement('接口详情', 'analysis')
            )}
          </div>
        </div>
      </ApiPage>
      <GraphPage active={section === 'graph'}>
        {selection.analysis ? (
          <StaticGraphPanel
            selected={{
              snapshot: snapshotId,
              analysis: selection.analysis,
              endpoint: selection.endpoint,
            }}
            node={selection.node}
            onNode={onNode}
            onSource={onSource}
            onFullGraph={
              selection.endpoint === null
                ? undefined
                : () =>
                    navigate({
                      ...selection,
                      endpoint: null,
                      node: null,
                      preview: null,
                      explanation: null,
                      attempt: null,
                      run: null,
                      system_run: null,
                      curriculum: null,
                      goal: null,
                      panel: null,
                      job: null,
                      section: 'graph',
                    })
            }
          />
        ) : (
          requirement('静态关系图', 'analysis')
        )}
      </GraphPage>
      <ImpactPage active={section === 'impact'}>
        {selection.analysis ? (
          <CandidateImpactPanel
            snapshot={snapshotId}
            analysis={selection.analysis}
            endpoint={selection.endpoint}
            node={selection.node}
            candidates={selection.candidates}
            onNode={onNode}
            onCandidates={(candidates) =>
              navigate({ ...selection, candidates })
            }
            onSource={onSource}
          />
        ) : (
          requirement('候选影响', 'analysis')
        )}
      </ImpactPage>
      <ExplanationPage active={section === 'explanation'}>
        {selected ? (
          <section className="surface module-summary">
            <ExplanationPanel
              key={selected.analysis + '.' + selected.endpoint}
              selected={selected}
              previewId={selection.preview}
              explanationId={selection.explanation}
              jobId={selection.job}
              onSelect={(value) =>
                navigate({
                  ...selection,
                  ...value,
                  panel: 'explanation',
                  section: 'explanation',
                })
              }
              onSource={onSource}
            />
          </section>
        ) : (
          requirement('模型讲解', 'endpoint')
        )}
      </ExplanationPage>
      <PracticePage active={section === 'labs'}>
        {selected ? (
          <div key={selected.analysis + '.' + selected.endpoint}>
            <nav className="module-local-tabs" aria-label="练习与实验内容">
              <button
                aria-pressed={!labMode}
                onClick={() =>
                  navigate({ ...selection, panel: 'learning', section: 'labs' })
                }
              >
                固定练习与复习
              </button>
              <button
                aria-pressed={labMode}
                onClick={() =>
                  navigate({ ...selection, panel: 'lab', section: 'labs' })
                }
              >
                受控实验
              </button>
            </nav>
            <section hidden={labMode} className="surface module-summary">
              <LearningPanel
                selected={selected}
                attemptId={selection.attempt}
                onAttempt={(attempt) =>
                  navigate({
                    ...selection,
                    attempt,
                    panel: 'learning',
                    section: 'labs',
                  })
                }
                onSource={onSource}
              />
            </section>
            <section
              hidden={!labMode}
              className="surface module-summary workspace-lab-panel"
            >
              <LabPanel
                selected={selected}
                runId={selection.run}
                systemRunId={selection.system_run}
                jobId={selection.job}
                onRun={(run) =>
                  navigate({
                    ...selection,
                    run,
                    system_run: null,
                    panel: 'lab',
                    section: 'labs',
                  })
                }
                onSystemRun={(system_run) =>
                  navigate({
                    ...selection,
                    system_run,
                    run: null,
                    panel: 'lab',
                    section: 'labs',
                  })
                }
                onJob={(job) =>
                  navigate({
                    ...selection,
                    run: null,
                    system_run: null,
                    job,
                    panel: 'lab',
                    section: 'labs',
                  })
                }
              />
            </section>
          </div>
        ) : (
          requirement('练习与实验', 'endpoint')
        )}
      </PracticePage>
    </>
  );
}
