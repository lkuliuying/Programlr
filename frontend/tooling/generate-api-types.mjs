import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { createClient } from '@hey-api/openapi-ts';
import ts from 'typescript';
import { format } from 'prettier';

if (process.argv.slice(2).some((arg) => arg !== '--check')) {
  throw new Error('只接受 --check 参数。');
}
const checkOnly = process.argv.includes('--check');

const runtime = resolve('../.runtime');
await mkdir(runtime, { recursive: true });
const temporary = await mkdtemp(join(runtime, 'api-types-'));
try {
  await createClient({
    input: '../contracts/openapi.yaml',
    output: { path: temporary, postProcess: [] },
    plugins: ['@hey-api/typescript'],
  });
  const source = ts.createSourceFile(
    'schema.d.ts',
    await readFile(join(temporary, 'types.gen.ts'), 'utf8'),
    ts.ScriptTarget.Latest,
    true,
  );
  if (
    source.statements.some(
      (node) =>
        !ts.isTypeAliasDeclaration(node) && !ts.isInterfaceDeclaration(node),
    )
  ) {
    throw new Error('生成器返回运行时代码，拒绝写入声明文件。');
  }
  const output = resolve('src/shared/api/generated/schema.d.ts');
  const declaration = await format(
    '// 从本工程 ../contracts/openapi.yaml 自动生成，请勿手工修改。\n' +
      ts.createPrinter({ removeComments: true }).printFile(source),
    { parser: 'typescript', singleQuote: true, trailingComma: 'all' },
  );
  if (checkOnly) {
    if (
      (await readFile(output, 'utf8')).replaceAll('\r\n', '\n') !== declaration
    ) {
      throw new Error(
        '前端类型已漂移，请先审阅契约，再运行 npm run api:types。',
      );
    }
    console.log('前端生成类型与本地契约一致。');
  } else {
    await mkdir(resolve('src/shared/api/generated'), { recursive: true });
    await writeFile(output, declaration);
  }
} finally {
  await rm(temporary, { recursive: true });
}
