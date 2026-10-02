import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
export const typePatches = JSON.parse(
  readFileSync(new URL('./type-patches.json', import.meta.url), 'utf8'),
);
const hash = (content) => createHash('sha256').update(content).digest('hex');

export function applyTypePatches(
  root = projectRoot,
  patches = typePatches,
  checkOnly = false,
) {
  const changes = [];
  for (const patch of patches) {
    const packageRoot = resolve(root, 'node_modules', patch.package);
    const installed = JSON.parse(
      readFileSync(resolve(packageRoot, 'package.json'), 'utf8'),
    );
    if (installed.version !== patch.version) {
      throw new Error(`类型补丁版本不匹配：${patch.package}`);
    }
    for (const file of patch.files) {
      const path = resolve(packageRoot, file);
      const within = relative(packageRoot, path);
      if (
        isAbsolute(within) ||
        within === '..' ||
        within.startsWith(`..${sep}`) ||
        !file.endsWith('.d.ts')
      ) {
        throw new Error('类型补丁路径不合法');
      }
      const original = readFileSync(path, 'utf8');
      if (hash(original) === patch.after_sha256) continue;
      if (checkOnly || hash(original) !== patch.before_sha256) {
        throw new Error(
          `类型补丁摘要不匹配或尚未应用：${patch.package}/${file}`,
        );
      }
      if (original.split(patch.before).length !== 2) {
        throw new Error('类型补丁替换位置不唯一');
      }
      const replacement = original.replace(patch.before, patch.after);
      if (hash(replacement) !== patch.after_sha256) {
        throw new Error('类型补丁目标摘要不匹配');
      }
      changes.push({ path, original, replacement });
    }
  }
  // 完成全部校验后才写入；文件系统故障时尽力恢复本次写入并显式报告恢复失败。
  const attempted = [];
  try {
    for (const change of changes) {
      attempted.push(change);
      writeFileSync(change.path, change.replacement, 'utf8');
    }
  } catch (error) {
    const failures = [error];
    for (const change of attempted.reverse()) {
      try {
        writeFileSync(change.path, change.original, 'utf8');
      } catch (restoreError) {
        failures.push(restoreError);
      }
    }
    throw new AggregateError(
      failures,
      '类型补丁写入失败；请检查安装目录并重新 npm ci',
      { cause: error },
    );
  }
  return changes.length;
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const changed = applyTypePatches();
  console.log(`类型补丁校验通过，本次修复 ${changed} 个声明文件`);
}
