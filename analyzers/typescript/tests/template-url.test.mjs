import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { analyze } from "../dist/parse-source.js";
import {
  decodeInput,
  encodeResult,
  PROTOCOL_VERSION,
} from "../dist/protocol.js";

function parse(sources) {
  const input = decodeInput({
    protocol_version: PROTOCOL_VERSION,
    snapshot_id: "00000000-0000-0000-0000-000000000001",
    sources: Object.entries(sources).map(([file_path, content]) => ({
      file_path,
      content,
    })),
  });
  const result = analyze(input);
  encodeResult(result, input);
  return result;
}

for (const group of ["development", "evaluation"]) {
  const data = JSON.parse(
    readFileSync(
      new URL(`../../../testdata/analysis/v02-${group}.json`, import.meta.url),
      "utf8",
    ),
  );
  for (const sample of data.cases.filter(
    (sample) => sample.kind === "frontend",
  )) {
    test(`常量模板样例 ${group}/${sample.id}`, () => {
      const result = parse(sample.frontend_sources);
      assert.deepEqual(
        result.requests.map((item) => [
          item.method,
          item.path,
          item.resolution,
        ]),
        sample.expected_requests.map((item) => item.slice(0, 3)),
      );
    });
  }
}

test("模板字符串只接受字符串且遵循深度和长度上限", () => {
  for (const expression of [
    "`${123}`",
    "`${true}`",
    "`${null}`",
    "`${{}}`",
    "`${String(123)}`",
  ]) {
    assert.equal(
      parse({ "api.ts": `fetch(${expression});` }).requests[0].resolution,
      "dynamic",
    );
  }
  assert.equal(
    parse({
      "api.ts": 'const root="' + "x".repeat(8192) + '";fetch(`/${root}`);',
    }).requests[0].resolution,
    "dynamic",
  );
  let code = "const part='/api/items/';\n";
  for (let i = 0; i < 36; i++)
    code += `const p${i}=\`${i ? "${p" + (i - 1) + "}" : "${part}"}\`;\n`;
  assert.equal(
    parse({ "api.ts": code + "fetch(p35);" }).requests[0].resolution,
    "dynamic",
  );
});

test("常量循环、写入、参数封装和非法文件保留不确定性", () => {
  for (const code of [
    "const a=`${b}`;const b=`${a}`;fetch(a);",
    "const root='/api/';root=choose();fetch(`${root}items/`);",
    "function wrap(url){return fetch(url);}wrap('/api/items/');",
  ])
    assert.ok(
      parse({ "api.ts": code }).requests.every(
        (item) => item.resolution !== "static",
      ),
    );
  assert.ok(
    parse({
      "bad.ts": "function broken( {",
      "ok.ts": "fetch(`/api/items/`);",
    }).diagnostics.some((item) => item.code === "FRONTEND_SYNTAX_ERROR"),
  );
});
