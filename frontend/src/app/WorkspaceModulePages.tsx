import type { ReactNode } from 'react';
import { Icon } from '../shared/components/Icon';
import { ScrollPanel } from '../shared/components/ScrollPanel';
import {
  PageHeading,
  ContentState,
} from '../shared/components/PagePresentation';
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
      <PageHeading
        title={title}
        description={description}
        icon={<Icon name={section} />}
        hidden={section === 'graph' || section === 'workbench'}
      />
      <div className="module-content">
        <ScrollPanel
          active={active}
          label={title}
          resetKey={params.toString() + '|' + context}
        >
          {children}
        </ScrollPanel>
      </div>
    </section>
  );
}
export function WorkbenchPage({ active, children }: PageProps) {
  return (
    <ModulePage
      active={active}
      section="workbench"
      title="工作台"
      description="从一个项目开始，读懂一条调用链。"
    >
      {children}
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
    <ContentState action={<button onClick={onAction}>{action}</button>}>
      <Icon name="folder" />
      <p>{message}</p>
    </ContentState>
  );
}
