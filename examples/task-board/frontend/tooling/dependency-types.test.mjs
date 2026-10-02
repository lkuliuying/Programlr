import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { test } from 'node:test';
import ts from 'typescript';

function diagnostics(source) {
  const config = ts.readConfigFile('tsconfig.json', ts.sys.readFile);
  const parsed = ts.parseJsonConfigFileContent(
    config.config,
    ts.sys,
    process.cwd(),
  );
  const file = resolve('tooling/dependency-type-input.ts');
  const host = ts.createCompilerHost(parsed.options);
  const original = host.readFile.bind(host);
  host.readFile = (name) => (resolve(name) === file ? source : original(name));
  return ts.getPreEmitDiagnostics(
    ts.createProgram([file], parsed.options, host),
  );
}

for (const module of ['es', 'lib']) {
  // 直接核对两种内部声明分发，不将这些内部路径用作产品导入接口。
  const imports = `
    import type { GroupPreviewConfig } from '../node_modules/@rc-component/image/${module}/PreviewGroup';
    import type { SinglePickerPanelProps } from '../node_modules/@rc-component/picker/${module}/PickerPanel/index';
  `;
  test(`${module} 声明保留图片组序号及面板可空值`, () => {
    const errors = diagnostics(`${imports}
      const render: GroupPreviewConfig['imageRender'] = (node, info) => {
        const current: number = info.current;
        return current ? node : null;
      };
      const empty: SinglePickerPanelProps<Date>['defaultValue'] = null;
      const date: SinglePickerPanelProps<Date>['defaultValue'] = new Date();
    `);
    assert.deepEqual(
      errors.map((error) =>
        ts.flattenDiagnosticMessageText(error.messageText, ' '),
      ),
      [],
    );
  });
  test(`${module} 声明仍拒绝错误回调参数和日期值`, () => {
    const errors = diagnostics(`${imports}
      const render: GroupPreviewConfig['imageRender'] = (node, info: { current: string }) => node;
      const invalid: SinglePickerPanelProps<Date>['defaultValue'] = 'invalid';
    `);
    assert.equal(errors.filter((error) => error.code === 2322).length, 2);
  });
}
