import { expect, test } from 'vitest';
import { folderBody, selectFolder } from './folder-validation';

function file(path: string, size = 1) {
  const item = new File(['x'], path.split('/').at(-1)!);
  Object.defineProperties(item, {
    webkitRelativePath: { value: path },
    size: { value: size },
  });
  return item;
}
test('精确排除秘密、依赖与构建，保留源码和受控声明', () => {
  const result = selectFolder(
    [
      'project/app/a.py',
      'project/web/a.tsx',
      'project/requirements-dev.txt',
      'project/pyproject.toml',
      'project/.env.local',
      'project/.venv/x.py',
      'project/node_modules/x.ts',
      'project/dist/a.js',
      'project/readme.txt',
      'project/.env.private/a.py',
      'project/secrets.py',
      'project/credentials.py',
    ].map((path) => file(path)),
  );
  expect(result.name).toBe('project');
  expect(result.entries.map((item) => item.path)).toEqual([
    'app/a.py',
    'pyproject.toml',
    'requirements-dev.txt',
    'web/a.tsx',
  ]);
  expect(result.excluded).toBe(8);
  const body = folderBody(result);
  expect(body.getAll('files')).toHaveLength(4);
  expect(body.get('manifest')).toBeInstanceOf(File);
});
test.each([
  'project/../x.py',
  'project/app\\a.py',
  'project/C:a.py',
  'project/con.py',
  'project/com¹.py',
  'project/a./x.py',
  'project//x.py',
])('危险路径 %s 在上传前拒绝', (path) => {
  expect(() => selectFolder([file(path)])).toThrow();
});
test('Unicode 归一化、大小写与文件目录碰撞拒绝', () => {
  expect(() => selectFolder([file('p/A.py'), file('p/a.py')])).toThrow(/冲突/);
  expect(() => selectFolder([file('p/e\u0301.py'), file('p/é.py')])).toThrow(
    /冲突/,
  );
  expect(() => selectFolder([file('p/a.py'), file('p/a.py/b.py')])).toThrow(
    /冲突/,
  );
});
test('单文件、数量和总容量边界执行独立预算', () => {
  expect(selectFolder([file('p/a.py', 1024 * 1024)]).entries).toHaveLength(1);
  expect(() => selectFolder([file('p/a.py', 1024 * 1024 + 1)])).toThrow(
    /1 MiB/,
  );
  expect(
    selectFolder(Array.from({ length: 2000 }, (_, i) => file(`p/${i}.py`)))
      .entries,
  ).toHaveLength(2000);
  expect(() =>
    selectFolder(Array.from({ length: 2001 }, (_, i) => file(`p/${i}.py`))),
  ).toThrow(/2000/);
  expect(
    selectFolder(
      Array.from({ length: 100 }, (_, i) => file(`p/${i}.py`, 1024 * 1024)),
    ).bytes,
  ).toBe(100 * 1024 * 1024);
  expect(() =>
    selectFolder(
      Array.from({ length: 101 }, (_, i) => file(`p/${i}.py`, 1024 * 1024)),
    ),
  ).toThrow(/100 MiB/);
  expect(() => selectFolder([file('p/logo.png')])).toThrow(/没有/);
});
