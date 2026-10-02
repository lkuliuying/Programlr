import type { ReactNode } from 'react';
import type {
  Project,
  Snapshot,
  SourceFile,
} from '../shared/api/generated/schema';
import { Icon } from '../shared/components/Icon';
import { ContentPager } from '../shared/components/ContentPager';
import { snapshotDisplayName } from '../features/projects';
import type { WorkspaceSection } from './workspace-location';

type PageProps = { active: boolean; children: ReactNode; context?: string };
function ModulePage({
  active,
  section,
  title,
  description,
  children,
  context = '',
}: PageProps & {
  section: WorkspaceSection;
  title: string;
  description: string;
}) {
  const params = new URLSearchParams(window.location.search);
  params.delete('section');
  params.delete('view');
  params.sort();
  return (
    <section
      hidden={!active}
      className={`module-page ${section}-module`}
      data-module={section}
      aria-label={`${title}页面`}
    >
      <header className={section === 'graph' ? 'sr-only' : 'module-heading'}>
        <Icon name={section} />
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </header>
      <div className="module-content">
        <ContentPager
          active={active}
          label={title}
          resetKey={params.toString() + '|' + context}
        >
          {children}
        </ContentPager>
      </div>
    </section>
  );
}
export function WorkbenchPage({
  active,
  project,
  snapshot,
  files,
  analysis,
  loading = false,
  unavailable = false,
  onSection,
}: {
  active: boolean;
  project: Project | undefined;
  snapshot: Snapshot | undefined;
  files: SourceFile[] | undefined;
  analysis: string | null;
  loading?: boolean;
  unavailable?: boolean;
  onSection: (section: WorkspaceSection) => void;
}) {
  const python = files?.filter((file) => file.file_path.endsWith('.py')).length;
  const frontend = files?.filter((file) =>
    /\.(tsx?|jsx?)$/.test(file.file_path),
  ).length;
  const step = !project ? 0 : !snapshot ? 1 : !analysis ? 2 : 3;
  const next = [
    ['创建或打开项目', 'import', '先建立一个学习空间，再导入想要读懂的源码。'],
    [
      '导入源码 ZIP',
      'import',
      '项目已打开。导入源码后，可以阅读文件并选择根路由进行分析。',
    ],
    [
      '选择根路由并分析',
      'api',
      '快照已准备好。显式选择根路由文件，开始一次静态分析。',
    ],
    [
      '继续阅读 API',
      'api',
      '已选择分析记录。从一条接口出发，核对定义、调用关系和源码依据。',
    ],
  ] as const;
  const current = next[step]!;
  const steps = [
    {
      title: '打开学习项目',
      description: '创建项目，或继续已有项目。',
      section: 'import',
      ready: !!project,
      enabled: true,
    },
    {
      title: '导入源码快照',
      description: project
        ? '选择 ZIP，保留这一次的源码版本。'
        : '先打开项目，再选择源码 ZIP。',
      section: 'import',
      ready: !!snapshot,
      enabled: !!project,
    },
    {
      title: '选择静态分析',
      description: snapshot
        ? '选择根路由提交分析，或读取已有记录。'
        : '导入快照后，再查看接口与静态关系。',
      section: 'api',
      ready: !!analysis,
      enabled: !!snapshot,
    },
  ] as const;
  return (
    <ModulePage
      active={active}
      section="workbench"
      title="工作台"
      description="从源码出发，逐步理解接口、数据流与背后的知识。"
    >
      {loading || unavailable ? (
        <section className="surface workbench-focus">
          <h2>{unavailable ? '当前项目暂不可用' : '正在读取当前项目…'}</h2>
          <p role={unavailable ? undefined : 'status'}>
            {unavailable
              ? '请使用上方错误提示重试，或重新选择项目与快照。'
              : '读取完成后，将显示当前快照和适合继续的步骤。'}
          </p>
          {unavailable && (
            <button onClick={() => onSection('import')}>重新选择项目</button>
          )}
        </section>
      ) : (
        <div className="workbench-module-grid">
          <section className="surface workbench-focus">
            <span className="workbench-eyebrow">
              {project ? '继续你的项目' : '开始使用'}
            </span>
            <h2>{project?.name ?? '从一个项目开始，读懂一条调用链'}</h2>
            <p className="workbench-intro">{current[2]}</p>
            <div className="module-actions">
              <button
                className="primary-button"
                onClick={() => onSection(current[1])}
              >
                {current[0]}
                <Icon name="arrow" />
              </button>
              {snapshot && (
                <button onClick={() => onSection('source')}>
                  打开源码阅读
                </button>
              )}
            </div>
            {snapshot ? (
              <div className="workbench-snapshot">
                <p>
                  <span>当前快照</span>
                  <strong>{snapshotDisplayName(snapshot)}</strong>
                </p>
                <dl className="module-facts">
                  <div>
                    <dt>已接收源码</dt>
                    <dd>
                      {snapshot.summary.accepted} <small>个文件</small>
                    </dd>
                  </div>
                  <div>
                    <dt>Python 源码</dt>
                    <dd>
                      {python === undefined ? '读取中' : python}{' '}
                      <small>个文件</small>
                    </dd>
                  </div>
                  <div>
                    <dt>前端源码</dt>
                    <dd>
                      {frontend === undefined ? '读取中' : frontend}{' '}
                      <small>个文件</small>
                    </dd>
                  </div>
                </dl>
              </div>
            ) : (
              <div className="workbench-preparation">
                <h3>开始前，准备这些就够了</h3>
                <ul>
                  <li>一个 DRF + React 项目的源码 ZIP，大小不超过 20 MiB。</li>
                  <li>打包前移除密钥、环境配置、依赖和构建产物。</li>
                </ul>
                <p>导入仅用于只读分析，不会安装依赖或执行你的项目。</p>
              </div>
            )}
          </section>
          <section
            className="surface workbench-guide"
            aria-label="项目准备步骤"
          >
            <h2>项目准备</h2>
            <ol className="workbench-steps">
              {steps.map((item, index) => (
                <li
                  key={item.title}
                  data-state={
                    item.ready
                      ? 'ready'
                      : index === step
                        ? 'current'
                        : 'waiting'
                  }
                  aria-current={index === step ? 'step' : undefined}
                >
                  <span className="workbench-step-number" aria-hidden="true">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div>
                    <button
                      disabled={!item.enabled}
                      onClick={() => onSection(item.section)}
                    >
                      {item.title}
                    </button>
                    <small>
                      {item.ready
                        ? '已选择'
                        : index === step
                          ? '当前步骤'
                          : '待准备'}
                    </small>
                    <p>{item.description}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="workbench-shortcuts">
              <button
                className="text-button"
                onClick={() => onSection('learning')}
              >
                先浏览知识卡片
                <Icon name="arrow" />
              </button>
              <button
                className="text-button"
                onClick={() => onSection('system')}
              >
                查看系统状态
              </button>
            </div>
          </section>
        </div>
      )}
    </ModulePage>
  );
}
export function ImportPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="import"
      title="项目导入"
      description="创建学习项目，将 ZIP 源码保存为不可变快照。"
    />
  );
}
export function SourcePage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="source"
      title="源码阅读"
      description="搜索文件并对照两个只读窗口，各自定位与分段阅读。"
    />
  );
}
export function ApiPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="api"
      title="API 分析"
      description="按方法和路径核对接口、前端请求及源码来源。"
    />
  );
}
export function GraphPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="graph"
      title="静态关系图"
      description="沿静态连接查看节点与依据；连接不代表运行轨迹。"
    />
  );
}
export function ComparisonPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="comparison"
      title="快照与对比"
      description="显式选择基准和目标，核对文件、接口与关系变化。"
    />
  );
}
export function ImpactPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="impact"
      title="候选影响"
      description="选择起点，阅读影响路径并处理待判断关系。"
    />
  );
}
export function KnowledgePage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="learning"
      title="知识与学习"
      description="阅读知识卡片，按目标和先修路径理解项目。"
    />
  );
}
export function PracticePage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="labs"
      title="练习与实验"
      description="先作答和预测，再查看固定题反馈与受控实验观测。"
    />
  );
}
export function ExplanationPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="explanation"
      title="模型讲解"
      description="审阅完整外发范围，单次确认后读取讲解及引用。"
    />
  );
}
export function SystemPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="system"
      title="系统状态"
      description="显式检查本地基础链路，核对数据库、队列与 Worker 的检查结果。"
    />
  );
}
export function TaskHistoryPage(props: PageProps) {
  return (
    <ModulePage
      {...props}
      section="jobs"
      title="任务历史"
      description="按时间查看执行记录、失败原因与任务结果。"
    />
  );
}
export function ModuleRequirement({
  message,
  action,
  onAction,
}: {
  message: string;
  action: string;
  onAction: () => void;
}) {
  return (
    <div className="surface module-requirement">
      <Icon name="folder" />
      <p>{message}</p>
      <button onClick={onAction}>{action}</button>
    </div>
  );
}
