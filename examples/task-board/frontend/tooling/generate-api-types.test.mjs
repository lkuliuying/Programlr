import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

test('生成检查拒绝漂移或缺失产物，并保留已有文件', async () => {
  const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const runtime = resolve(frontend, '../.runtime');
  await mkdir(runtime, { recursive: true });
  const temporary = await mkdtemp(join(runtime, 'generation-test-'));
  try {
    const cwd = join(temporary, 'frontend');
    const output = join(cwd, 'src/shared/api/generated/schema.d.ts');
    await mkdir(dirname(output), { recursive: true });
    await mkdir(join(temporary, 'contracts'));
    await writeFile(
      join(temporary, 'contracts/openapi.yaml'),
      await readFile(resolve(frontend, '../contracts/openapi.yaml')),
    );
    const script = join(frontend, 'tooling/generate-api-types.mjs');
    const options = { cwd, encoding: 'utf8', timeout: 60000 };
    const missing = spawnSync(process.execPath, [script, '--check'], options);
    assert.equal(missing.status, 1);
    assert.match(missing.stderr, /ENOENT/);
    execFileSync(process.execPath, [script], options);
    const generated = await readFile(output, 'utf8');
    execFileSync(process.execPath, [script, '--check'], options);
    assert.equal(await readFile(output, 'utf8'), generated);
    const changed = generated + '\n// 测试人为漂移。\n';
    await writeFile(output, changed);
    const stale = spawnSync(process.execPath, [script, '--check'], options);
    assert.equal(stale.status, 1);
    assert.match(stale.stderr, /前端类型已漂移/);
    assert.equal(await readFile(output, 'utf8'), changed);
  } finally {
    assert.ok(
      temporary.startsWith(runtime + '/') ||
        temporary.startsWith(runtime + '\\'),
    );
    await rm(temporary, { recursive: true });
  }
});
