import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { applyTypePatches } from './apply-type-patches.mjs';

const original = 'interface Child extends Parent {}\n';
const replacement = "interface Child extends Omit<Parent, 'value'> {}\n";
const hash = (text) => createHash('sha256').update(text).digest('hex');

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'm1-type-patches-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const directory = join(root, 'node_modules', 'fixture');
  mkdirSync(directory, { recursive: true });
  writeFileSync(
    join(directory, 'package.json'),
    JSON.stringify({ version: '1.0.0' }),
  );
  for (const file of ['first.d.ts', 'second.d.ts'])
    writeFileSync(join(directory, file), original);
  const patch = {
    package: 'fixture',
    version: '1.0.0',
    files: ['first.d.ts', 'second.d.ts'],
    before: 'extends Parent',
    after: "extends Omit<Parent, 'value'>",
    before_sha256: hash(original),
    after_sha256: hash(replacement),
  };
  return { root, directory, patch };
}

test('首次应用、重复应用和只读校验保持一致', (t) => {
  const { root, directory, patch } = fixture(t);
  assert.throws(() => applyTypePatches(root, [patch], true), /尚未应用/);
  assert.equal(applyTypePatches(root, [patch]), 2);
  assert.equal(
    readFileSync(join(directory, 'first.d.ts'), 'utf8'),
    replacement,
  );
  assert.equal(applyTypePatches(root, [patch]), 0);
  assert.equal(applyTypePatches(root, [patch], true), 0);
});

for (const failure of ['version', 'digest', 'missing', 'target', 'path']) {
  test(`拒绝 ${failure} 异常且不会部分修改`, (t) => {
    const { root, directory, patch } = fixture(t);
    if (failure === 'version') patch.version = '2.0.0';
    if (failure === 'digest')
      writeFileSync(join(directory, 'second.d.ts'), 'unknown');
    if (failure === 'missing') rmSync(join(directory, 'second.d.ts'));
    if (failure === 'target') patch.after_sha256 = '0'.repeat(64);
    if (failure === 'path') patch.files.push('../outside.d.ts');
    assert.throws(() => applyTypePatches(root, [patch]));
    assert.equal(readFileSync(join(directory, 'first.d.ts'), 'utf8'), original);
  });
}
