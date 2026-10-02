import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { applyTypePatches } from './apply-type-patches.mjs';

const root = new URL('../', import.meta.url);
applyTypePatches(fileURLToPath(root), undefined, true);
const readJson = (path) =>
  JSON.parse(readFileSync(new URL(path, root), 'utf8'));
const manifest = readJson('package.json');
const lock = readJson('package-lock.json');
const expectedNode = readFileSync(
  new URL('.node-version', root),
  'utf8',
).trim();
assert.equal(process.versions.node, expectedNode, 'Node 版本与锁定记录不一致');
assert.equal(manifest.engines.node, expectedNode);
assert.ok(process.env.npm_execpath, '请通过 npm run verify:versions 执行');
const npmVersion = execFileSync(
  process.execPath,
  [process.env.npm_execpath, '--version'],
  { encoding: 'utf8', timeout: 10000 },
).trim();
assert.equal(manifest.packageManager, `npm@${npmVersion}`);
assert.equal(manifest.engines.npm, npmVersion);
const observed = { node: process.versions.node, npm: npmVersion };
for (const [name, expected] of Object.entries({
  ...manifest.dependencies,
  ...manifest.devDependencies,
})) {
  assert.match(expected, /^\d+\.\d+\.\d+$/, '直接依赖必须精确锁定');
  const installed = readJson(`node_modules/${name}/package.json`);
  assert.equal(installed.version, expected, `${name} 安装版本不匹配`);
  assert.equal(lock.packages[`node_modules/${name}`].version, expected);
  observed[name] = installed.version;
}

// 负向检查使用工具 API 和内存输入，不产生需要提交的错误样例。
const { ESLint } = await import('eslint');
const eslint = new ESLint({ cwd: fileURLToPath(root) });
const results = await eslint.lintText('undefinedToolchainName();', {
  filePath: 'tooling/lint-probe.mjs',
});
assert.ok(results[0].messages.some((message) => message.ruleId === 'no-undef'));
const ts = await import('typescript');
const fileName = '/toolchain-type-probe.ts';
const options = { strict: true, noEmit: true, noLib: true, types: [] };
const host = ts.createCompilerHost(options);
host.getSourceFile = (name, languageVersion) =>
  name === fileName
    ? ts.createSourceFile(
        name,
        'const count: number = "invalid";',
        languageVersion,
      )
    : undefined;
const program = ts.createProgram([fileName], options, host);
assert.ok(
  program
    .getSemanticDiagnostics()
    .some((diagnostic) => diagnostic.code === 2322),
);
console.log(JSON.stringify(observed, null, 2));
console.log('ESLint 与 TypeScript 负向检查通过');
