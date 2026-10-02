import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { analyze } from '../dist/parse-source.js';
import {
  decodeInput,
  encodeResult,
  PROTOCOL_VERSION,
} from '../dist/protocol.js';

const snapshot = '00000000-0000-0000-0000-000000000001';
const input = (files) =>
  decodeInput({
    protocol_version: PROTOCOL_VERSION,
    snapshot_id: snapshot,
    sources: Object.entries(files).map(([file_path, content]) => ({
      file_path,
      content,
    })),
  });
const parse = (files) => {
  const data = input(files);
  const result = analyze(data);
  encodeResult(result, data);
  return result;
};

test('静态 fetch、常量别名与默认方法保留引用', () => {
  const result = parse({
    'api.ts':
      "const prefix='/api/'; const route=prefix+'tasks/'; export function create() { return fetch(route,{method:'post'}); } fetch('/health/?token=synthetic');",
  });
  assert.deepEqual(
    result.requests.map((r) => [r.method, r.path, r.resolution]),
    [
      ['POST', '/api/tasks/', 'static'],
      ['GET', '/health/', 'static'],
    ],
  );
  assert.ok(!JSON.stringify(result).includes('synthetic'));
  assert.equal(result.requests[0].source_ref.snapshot_id, snapshot);
});

test('axios 实例、直接配置及未知基础路径不会混淆', () => {
  const result = parse({
    'api.ts': `import axios from 'axios';
    const client=axios.create({baseURL:'/api/v1/'});
    client.post('tasks/',{});
    axios({url:'/other/', method:'put'});
    const unknown=axios.create({baseURL:process.env.BASE}); unknown.get('/tasks/');
    axios.get('https://example.invalid/tasks/?key=synthetic');`,
  });
  assert.deepEqual(
    result.requests.map((r) => [r.method, r.path, r.resolution]),
    [
      ['POST', '/api/v1/tasks/', 'static'],
      ['PUT', '/other/', 'static'],
      ['GET', '/tasks/', 'unknown_base'],
      ['GET', '/tasks/', 'external'],
    ],
  );
  assert.ok(!JSON.stringify(result).includes('synthetic'));
});

test('axios 默认方法按实例配置继承，自定义传输及客户端逃逸不确认', () => {
  const result = parse({
    'method.ts': `import axios from 'axios';
    const client=axios.create({baseURL:'/api/',method:'POST'});
    client('tasks/'); client.request({url:'tasks/',method:'PUT'}); client.get('tasks/');`,
    'custom.ts': `import axios from 'axios';
    const client=axios.create({baseURL:'/api/',adapter:customAdapter});
    client.post('tasks/',{}, {baseURL:'/override/'});
    axios.post('/tasks/', {}, {transformRequest:changeTarget});`,
    'escape.ts': `import axios from 'axios';
    const client=axios.create({baseURL:'/api/'}); configure(client); client.get('tasks/');`,
  });
  const defaults = result.requests.filter(
    (r) => r.source_ref.file_path === 'method.ts',
  );
  assert.deepEqual(
    defaults.map((r) => [r.method, r.path, r.resolution]),
    [
      ['POST', '/api/tasks/', 'static'],
      ['PUT', '/api/tasks/', 'static'],
      ['GET', '/api/tasks/', 'static'],
    ],
  );
  const uncertain = result.requests.filter(
    (r) => r.source_ref.file_path !== 'method.ts',
  );
  assert.equal(uncertain.length, 3);
  assert.ok(uncertain.every((r) => r.resolution !== 'static'));
});

test('fetch 常量别名可识别，动态或重复 JSX 绑定不伪造入口', () => {
  const result = parse({
    'entry.tsx': `import {Form} from 'antd';
    const send=fetch; const alias=send; alias('/alias/');
    function submit(){send('/submit/',{method:'POST'});}
    const invalid=<Form onFinish={submit} {...props}/>;
    const duplicate=<button onClick={submit} onClick={other}/>;
    const valid=<Form {...props} onFinish={submit}/>;`,
  });
  assert.deepEqual(
    result.requests.map((r) => r.path),
    ['/alias/', '/submit/'],
  );
  const handler = result.functions.find((f) => f.name === 'submit');
  assert.equal(handler.entry_points.length, 1);
  assert.equal(handler.entry_points[0].source_ref.start_line, 6);
  assert.ok(result.diagnostics.some((d) => d.code === 'JSX_BINDING_DYNAMIC'));
});

test('遮蔽 fetch、动态配置、可变 URL 与重复配置不产生确认', () => {
  const result = parse({
    'api.js': `function local(fetch){ fetch('/wrong/'); }
    let url='/before/'; url='/after/'; fetch(url);
    fetch('/spread/',{...options}); fetch('/repeat/',{method:'GET',method:'POST'});
    fetch('/dynamic/'+value);`,
  });
  assert.equal(result.requests.length, 4);
  assert.ok(result.requests.every((r) => r.resolution === 'dynamic'));
});

test('配置经别名修改或逃逸时降级，axios 别名和参数优先级保守解析', () => {
  const result = parse({
    'api.ts': `import axios, {isAxiosError} from 'axios';
    const config={method:'POST'}; const alias=config; alias.method='DELETE'; fetch('/changed/',config);
    const other={method:'POST'}; configure(other); fetch('/escaped/',other);
    const client=axios; client.get('/actual/',{url:'/ignored/',method:'POST'});
    isAxiosError('/not-request/');
    const bad=axios.create({baseURL:'/api/?prefix=1'}); bad.get('tasks/');
    const send=()=>fetch('/function/'); const sendAlias=send; function entry(){sendAlias();}`,
  });
  assert.deepEqual(
    result.requests.slice(0, 4).map((r) => [r.path, r.resolution]),
    [
      ['/changed/', 'dynamic'],
      ['/escaped/', 'dynamic'],
      ['/actual/', 'static'],
      [null, 'unsupported'],
    ],
  );
  assert.equal(result.requests.length, 5);
  const entry = result.functions.find((f) => f.name === 'entry'),
    send = result.functions.find((f) => f.name === 'send');
  assert.ok(
    result.relations.some(
      (r) =>
        r.relation === 'direct_call' &&
        r.source_id === entry.id &&
        r.target_id === send.id,
    ),
  );
});

test('唯一相对导入与本地循环调用有界，重名文件不会任意选择', () => {
  const result = parse({
    'a.ts': `import {send as create} from './b'; export function start(){create();} function loop(){loop();}`,
    'b.ts': `export function send(){fetch('/api/');}`,
  });
  const start = result.functions.find((f) => f.name === 'start');
  const send = result.functions.find((f) => f.name === 'send');
  assert.ok(
    result.relations.some(
      (r) =>
        r.relation === 'direct_call' &&
        r.source_id === start.id &&
        r.target_id === send.id,
    ),
  );
  const ambiguous = parse({
    'a.ts': `import {send} from './b'; function start(){send();}`,
    'b.ts': 'export function send(){}',
    'b.js': 'export function send(){}',
  });
  assert.ok(
    ambiguous.diagnostics.some((d) => d.code === 'UNRESOLVED_LOCAL_IMPORT'),
  );
  assert.equal(
    ambiguous.relations.filter((r) => r.relation === 'direct_call').length,
    0,
  );
});

test('单文件语法错误保留其他文件，输入不执行', () => {
  const result = parse({
    'bad.ts': 'function broken( {',
    'good.ts': `throw new Error('must-not-run'); fetch('/ok/');`,
  });
  assert.equal(result.coverage.syntax_failed_files, 1);
  assert.equal(result.requests[0].path, '/ok/');
  assert.equal(result.coverage.complete, false);
});

test('源码引用遵循快照 LF 行号，AST 数量预算拒绝超限输入', () => {
  const result = parse({ 'unicode.ts': "// 注释\u2028fetch('/api/');\n" });
  assert.equal(result.requests[0].source_ref.start_line, 1);
  assert.throws(
    () => parse({ 'large.js': 'x();'.repeat(170000) }),
    (error) => error.reason === 'ast_node_limit',
  );
});

test('现有任务示例入口经有限框架规则到达创建请求', () => {
  const root = fileURLToPath(
    new URL('../../../examples/task-board/frontend/src/', import.meta.url),
  );
  const files = {};
  function collect(folder) {
    for (const entry of readdirSync(folder, { withFileTypes: true })) {
      const full = path.join(folder, entry.name);
      if (entry.isDirectory()) collect(full);
      else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.includes('.test.'))
        files[
          'frontend/src/' + path.relative(root, full).replaceAll('\\', '/')
        ] = readFileSync(full, 'utf8');
    }
  }
  collect(root);
  const result = parse(files);
  const handler = result.functions.find((f) => f.name === 'handleSubmit');
  const request = result.requests.find(
    (r) => r.method === 'POST' && r.path === '/api/v1/tasks/',
  );
  assert.ok(
    handler.entry_points.some((e) => e.rule === 'antd/6.form_on_finish'),
  );
  const seen = new Set(),
    pending = [handler.id];
  while (pending.length) {
    const id = pending.pop();
    if (seen.has(id)) continue;
    seen.add(id);
    for (const r of result.relations)
      if (r.source_id === id) pending.push(r.target_id);
  }
  assert.ok(seen.has(request.id));
  assert.ok(
    result.relations.some(
      (r) =>
        r.relation === 'callback_binding' &&
        r.evidence[0].kind === 'framework_rule',
    ),
  );
});

test('协议拒绝越界路径、重复输入与非法版本', () => {
  for (const file of [
    '/host.ts',
    '../out.ts',
    'a/../b.ts',
    'a\\b.ts',
    'a//b.ts',
  ])
    assert.throws(() => input({ [file]: '' }));
  assert.throws(() =>
    decodeInput({
      protocol_version: 'other',
      snapshot_id: snapshot,
      sources: [],
    }),
  );
  const data = input({ 'a.ts': '' });
  data.sources.push(data.sources[0]);
  assert.throws(() => decodeInput(data));
});

test('CLI 只输出 JSON，错误不回显输入', () => {
  const cli = fileURLToPath(new URL('../dist/cli.js', import.meta.url));
  const bad = spawnSync(process.execPath, [cli], {
    input: 'synthetic-private-data',
    encoding: 'utf8',
    timeout: 5000,
  });
  assert.equal(bad.status, 2);
  assert.equal(bad.stderr, '');
  assert.equal(JSON.parse(bad.stdout).failure, 'parser_failed');
  assert.ok(!bad.stdout.includes('synthetic-private-data'));
  const good = spawnSync(process.execPath, [cli], {
    input: JSON.stringify(input({ 'a.ts': `fetch('/ok/')` })),
    encoding: 'utf8',
    timeout: 5000,
  });
  assert.equal(good.status, 0);
  assert.equal(JSON.parse(good.stdout).requests.length, 1);
});
