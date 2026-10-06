import type { WorkspaceSection } from './workspace-location';

export const navigation = [
  ['import', '项目管理'],
  ['source', '项目工作区'],
  ['jobs', '操作日志'],
] as const;

export const navigationGroups = [
  { id: 'workbench', label: '项目管理', sections: ['import'] },
  {
    id: 'project',
    label: '项目工作区',
    sections: ['source'],
  },
  { id: 'system', label: '操作日志', sections: ['jobs'] },
] as const satisfies ReadonlyArray<{
  id: string;
  label: string;
  sections: readonly WorkspaceSection[];
}>;

export type WorkspaceCategory = (typeof navigationGroups)[number]['id'];
export type RecentSections = Record<WorkspaceCategory, WorkspaceSection>;

const sectionCategories: Record<WorkspaceSection, WorkspaceCategory> = {
  workbench: 'workbench',
  import: 'workbench',
  source: 'project',
  api: 'project',
  graph: 'project',
  comparison: 'system',
  impact: 'system',
  learning: 'project',
  labs: 'system',
  explanation: 'project',
  system: 'system',
  jobs: 'system',
};

export function workspaceCategory(
  section: WorkspaceSection,
): WorkspaceCategory {
  return sectionCategories[section];
}

export function rememberSection(
  recent: RecentSections,
  section: WorkspaceSection,
): RecentSections {
  const category = workspaceCategory(section);
  return recent[category] === section
    ? recent
    : {
        ...recent,
        [category]:
          category === 'workbench'
            ? 'import'
            : category === 'project'
              ? 'source'
              : 'jobs',
      };
}

export function initialRecentSections(
  section: WorkspaceSection,
): RecentSections {
  // 分类记忆仅存于当前外壳实例，刷新后从已校验的 URL 模块重新开始。
  return rememberSection(
    {
      workbench: 'import',
      project: 'source',
      system: 'jobs',
    },
    section,
  );
}
