import type { ReactNode } from 'react';
import type {
  Project,
  Snapshot,
  SourceFile,
} from '../shared/api/generated/schema';
import { Icon } from '../shared/components/Icon';
import type { WorkspaceSection } from './workspace-location';

type PageProps = { active: boolean; children: ReactNode };
function ModulePage({
  active,
  section,
  title,
  description,
  children,
}: PageProps & {
  section: WorkspaceSection;
  title: string;
  description: string;
}) {
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
      <div className="module-content">{children}</div>
    </section>
  );
}
export function WorkbenchPage({
  active,
  project,
  snapshot,
  files,
  analysis,
  onSection,
}: {
  active: boolean;
  project: Project | undefined;
  snapshot: Snapshot | undefined;
  files: SourceFile[] | undefined;
  analysis: string | null;
  onSection: (section: WorkspaceSection) => void;
}) {
  const python = files?.filter((file) => file.file_path.endsWith('.py')).length;
  const frontend = files?.filter((file) =>
    /\.(tsx?|jsx?)$/.test(file.file_path),
  ).length;
  return (
    <ModulePage
      active={active}
      section="workbench"
      title="工作台"
      description="确认项目准备状态，选择下一步阅读与学习。"
    >
      <div className="workbench-module-grid">
        <section className="surface module-summary">
          <h2>{project?.name ?? '打开一个学习项目'}</h2>
          <p>导入源码仅供只读分析，学习与实验使用固定可信内容。</p>
          <dl className="module-facts">
            <div>
              <dt>已接收源码</dt>
              <dd>
                {snapshot
                  ? `${snapshot.summary.accepted} 个文件`
                  : '尚未选择快照'}
              </dd>
            </div>
            <div>
              <dt>Python 源码</dt>
              <dd>{python === undefined ? '未读取' : `${python} 个文件`}</dd>
            </div>
            <div>
              <dt>前端源码</dt>
              <dd>
                {frontend === undefined ? '未读取' : `${frontend} 个文件`}
              </dd>
            </div>
          </dl>
          <ol className="readiness-list">
            <li>项目：{project ? '已打开' : '等待选择'}</li>
            <li>快照：{snapshot ? '已选择' : '等待导入或选择'}</li>
            <li>
              分析：
              {analysis
                ? '已选择记录，请在 API 分析核对结果'
                : '等待选择或显式提交'}
            </li>
          </ol>
          <div className="module-actions">
            <button
              className="primary-button"
              onClick={() => onSection(project && snapshot ? 'api' : 'import')}
            >
              {project && snapshot ? '进入 API 分析' : '前往项目导入'}
            </button>
            <button onClick={() => onSection('source')}>打开源码阅读</button>
          </div>
        </section>
        <section className="surface module-summary">
          <h2>下一步</h2>
          <ol className="module-next-steps">
            <li>
              <button onClick={() => onSection('api')}>从一条接口开始</button>
              <p>核对方法、路径、后端对象和前端请求来源。</p>
            </li>
            <li>
              <button onClick={() => onSection('learning')}>
                建立知识路径
              </button>
              <p>阅读已发布卡片，确认先修知识。</p>
            </li>
            <li>
              <button onClick={() => onSection('labs')}>完成练习与实验</button>
              <p>先作答和预测，再查看反馈与实际观测。</p>
            </li>
          </ol>
          <button className="text-button" onClick={() => onSection('jobs')}>
            查看系统与任务
          </button>
        </section>
      </div>
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
      section="jobs"
      title="系统与任务"
      description="显式检查环境，追踪任务的持久化状态与结果。"
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
