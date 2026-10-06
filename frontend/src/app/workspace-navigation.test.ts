import { expect, test } from 'vitest';
import {
  initialRecentSections,
  navigation,
  navigationGroups,
  rememberSection,
  workspaceCategory,
} from './workspace-navigation';

test('三条主入口完整且唯一，退役功能不进入活动导航', () => {
  expect(navigation.map(([, label]) => label)).toEqual([
    '项目管理',
    '项目工作区',
    '操作日志',
  ]);
  expect(navigationGroups.flatMap((group) => [...group.sections])).toEqual(
    navigation.map(([section]) => section),
  );
  expect(new Set(navigation.map(([section]) => section)).size).toBe(3);
});
test('旧源码与讲解链接映射同一工作区，退役链接有独立说明位置', () => {
  for (const section of [
    'source',
    'api',
    'graph',
    'learning',
    'explanation',
  ] as const)
    expect(workspaceCategory(section)).toBe('project');
  for (const section of ['labs', 'impact', 'comparison', 'system'] as const)
    expect(workspaceCategory(section)).toBe('system');
  expect(workspaceCategory('workbench')).toBe('workbench');
});
test('分类入口稳定，工作区面板不会变成独立主入口', () => {
  const original = initialRecentSections('api');
  expect(original).toEqual({
    workbench: 'import',
    project: 'source',
    system: 'jobs',
  });
  expect(rememberSection(original, 'graph')).toEqual(original);
  expect(initialRecentSections('explanation')).toEqual(original);
});
