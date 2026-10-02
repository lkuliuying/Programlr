export const PROTOCOL_VERSION = "typescript-analysis/1.0.0";
export const RULE_VERSION = "typescript-react/1.1.0";
export const MAX_INPUT_BYTES = 128 * 1024 * 1024;
export const MAX_OUTPUT_BYTES = 8 * 1024 * 1024;
export const MAX_NODES = 500_000;
export const MAX_ITEMS = 10_000;

export interface SourceRef {
  snapshot_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
}
export interface Evidence {
  kind: "source_fact" | "static_inference" | "framework_rule";
  rule: string;
  source_ref: SourceRef;
}
export interface Input {
  protocol_version: string;
  snapshot_id: string;
  sources: { file_path: string; content: string }[];
}
export interface FunctionInfo {
  id: string;
  name: string;
  source_ref: SourceRef;
  entry_points: Evidence[];
}
export interface RequestInfo {
  id: string;
  owner_id: string | null;
  method: string | null;
  original_path: string | null;
  path: string | null;
  resolution:
    "static" | "unknown_base" | "dynamic" | "external" | "unsupported";
  source_ref: SourceRef;
  evidence: Evidence[];
}
export interface Relation {
  source_id: string;
  target_id: string;
  relation:
    | "direct_call"
    | "contains_function"
    | "contains_request"
    | "callback_binding";
  evidence: Evidence[];
}
export interface Diagnostic {
  code: string;
  message: string;
  severity: "warning";
  source_ref: SourceRef | null;
}
export interface Result {
  protocol_version: string;
  rule_version: string;
  snapshot_id: string;
  functions: FunctionInfo[];
  requests: RequestInfo[];
  relations: Relation[];
  diagnostics: Diagnostic[];
  coverage: {
    source_files: number;
    parsed_files: number;
    syntax_failed_files: number;
    function_count: number;
    request_count: number;
    complete: boolean;
    limitations: string[];
  };
}

export class ParseFailure extends Error {
  constructor(readonly reason: string) {
    super("前端静态分析失败。");
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function decodeInput(value: unknown): Input {
  if (
    !record(value) ||
    Object.keys(value).sort().join() !==
      "protocol_version,snapshot_id,sources" ||
    value.protocol_version !== PROTOCOL_VERSION ||
    typeof value.snapshot_id !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(
      value.snapshot_id,
    ) ||
    !Array.isArray(value.sources) ||
    value.sources.length > 2000
  )
    throw new ParseFailure("invalid_input");
  const paths = new Set<string>();
  let bytes = 0;
  const sources = value.sources.map((source: unknown) => {
    if (
      !record(source) ||
      Object.keys(source).sort().join() !== "content,file_path" ||
      typeof source.file_path !== "string" ||
      typeof source.content !== "string" ||
      source.file_path.length > 1024 ||
      /[\\:\x00-\x1f]/.test(source.file_path) ||
      source.file_path
        .split("/")
        .some((part) => !part || part === "." || part === "..") ||
      !/\.(js|jsx|ts|tsx)$/.test(source.file_path) ||
      paths.has(source.file_path)
    )
      throw new ParseFailure("invalid_input");
    paths.add(source.file_path);
    const length = Buffer.byteLength(source.content);
    bytes += length;
    if (length > 1024 * 1024 || bytes > 100 * 1024 * 1024)
      throw new ParseFailure("input_limit");
    return { file_path: source.file_path, content: source.content };
  });
  return {
    protocol_version: PROTOCOL_VERSION,
    snapshot_id: value.snapshot_id,
    sources,
  };
}

export function encodeResult(result: Result, input: Input): string {
  const counts = new Map(
    input.sources.map((s) => [
      s.file_path,
      Math.max(
        1,
        s.content.split("\n").length - (s.content.endsWith("\n") ? 1 : 0),
      ),
    ]),
  );
  const ids = new Set(
    [...result.functions, ...result.requests].map((item) => item.id),
  );
  const ref = (value: SourceRef) => {
    if (
      value.snapshot_id !== input.snapshot_id ||
      !counts.has(value.file_path) ||
      value.start_line < 1 ||
      value.end_line < value.start_line ||
      value.end_line > counts.get(value.file_path)!
    )
      throw new ParseFailure("invalid_output");
  };
  for (const items of [
    result.functions,
    result.requests,
    result.relations,
    result.diagnostics,
  ]) {
    if (items.length > MAX_ITEMS) throw new ParseFailure("result_limit");
  }
  if (ids.size !== result.functions.length + result.requests.length)
    throw new ParseFailure("invalid_output");
  for (const item of [...result.functions, ...result.requests])
    ref(item.source_ref);
  for (const item of result.functions)
    for (const evidence of item.entry_points) ref(evidence.source_ref);
  for (const item of result.requests) {
    if (
      item.owner_id !== null &&
      !result.functions.some((fn) => fn.id === item.owner_id)
    )
      throw new ParseFailure("invalid_output");
    for (const evidence of item.evidence) ref(evidence.source_ref);
  }
  for (const item of result.relations) {
    if (
      !ids.has(item.source_id) ||
      !ids.has(item.target_id) ||
      !item.evidence.length
    )
      throw new ParseFailure("invalid_output");
    for (const evidence of item.evidence) ref(evidence.source_ref);
  }
  for (const item of result.diagnostics)
    if (item.source_ref) ref(item.source_ref);
  const text = JSON.stringify(result);
  if (Buffer.byteLength(text) > MAX_OUTPUT_BYTES)
    throw new ParseFailure("output_limit");
  return text;
}
