import { createHash } from "node:crypto";
import path from "node:path";
import ts from "typescript";
import {
  MAX_ITEMS,
  MAX_NODES,
  ParseFailure,
  PROTOCOL_VERSION,
  RULE_VERSION,
  type Evidence,
  type Input,
  type RequestInfo,
  type Result,
  type SourceRef,
} from "./protocol.js";

const METHODS = new Set([
  "GET",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
  "HEAD",
  "OPTIONS",
  "TRACE",
]);
type Callable =
  | ts.FunctionDeclaration
  | ts.FunctionExpression
  | ts.ArrowFunction
  | ts.MethodDeclaration;
const isFunction = (node: ts.Node): node is Callable =>
  ts.isFunctionDeclaration(node) ||
  ts.isFunctionExpression(node) ||
  ts.isArrowFunction(node) ||
  ts.isMethodDeclaration(node);

export function analyze(input: Input): Result {
  const prefix = "/__snapshot__/";
  const sources = new Map(
    input.sources.map((source) => [prefix + source.file_path, source.content]),
  );
  const sourceFiles = new Map<string, ts.SourceFile>();
  const result: Result = {
    protocol_version: PROTOCOL_VERSION,
    rule_version: RULE_VERSION,
    snapshot_id: input.snapshot_id,
    functions: [],
    requests: [],
    relations: [],
    diagnostics: [],
    coverage: {
      source_files: input.sources.length,
      parsed_files: 0,
      syntax_failed_files: 0,
      function_count: 0,
      request_count: 0,
      complete: true,
      limitations: [
        "静态关联不代表实际执行；只解析给定源码中的唯一相对导入和直接调用。",
        "动态 URL、运行时代理、复杂封装、外部模块及可变客户端配置不自动补全。",
        "回调规则限 React DOM 事件、Ant Design 6 Form.onFinish 与 TanStack Query 5 mutationFn。",
      ],
    },
  };
  function resolve(name: string, containing: string): string | undefined {
    if (!name.startsWith(".")) return undefined;
    const base = path.posix.normalize(
      path.posix.join(path.posix.dirname(containing), name),
    );
    if (!base.startsWith(prefix)) return undefined;
    if (sources.has(base)) return base;
    const extensionless = /\.[cm]?jsx?$/.test(base)
      ? base.replace(/\.[cm]?jsx?$/, "")
      : base;
    const candidates = [
      ...new Set([
        ...[".ts", ".tsx", ".js", ".jsx"].map((ext) => extensionless + ext),
        ...[".ts", ".tsx", ".js", ".jsx"].map((ext) => base + "/index" + ext),
      ]),
    ].filter((candidate) => sources.has(candidate));
    return candidates.length === 1 ? candidates[0] : undefined;
  }
  const host: ts.CompilerHost = {
    getSourceFile: (name, languageVersion) => {
      const text = sources.get(name);
      if (text === undefined) return undefined;
      if (!sourceFiles.has(name))
        sourceFiles.set(
          name,
          ts.createSourceFile(name, text, languageVersion, true),
        );
      return sourceFiles.get(name);
    },
    getDefaultLibFileName: () => "",
    writeFile: () => {
      throw new ParseFailure("unexpected_emit");
    },
    getCurrentDirectory: () => prefix,
    getDirectories: () => [],
    fileExists: (name) => sources.has(name),
    readFile: (name) => sources.get(name),
    getCanonicalFileName: (name) => name,
    useCaseSensitiveFileNames: () => true,
    getNewLine: () => "\n",
    resolveModuleNames: (names, containing) =>
      names.map((name) => {
        const file = resolve(name, containing);
        return file ? { resolvedFileName: file } : undefined;
      }),
  };
  const program = ts.createProgram(
    [...sources.keys()],
    {
      noLib: true,
      noEmit: true,
      allowJs: true,
      jsx: ts.JsxEmit.Preserve,
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
    },
    host,
  );
  const checker = program.getTypeChecker();
  const nodes: ts.Node[] = [];
  const valid = new Set<ts.SourceFile>();
  const lineOffsets = new Map<ts.SourceFile, number[]>();
  function ref(node: ts.Node): SourceRef {
    const file = node.getSourceFile();
    let offsets = lineOffsets.get(file);
    if (!offsets) {
      offsets = [0];
      for (let index = 0; index < file.text.length; index++)
        if (file.text[index] === "\n") offsets.push(index + 1);
      lineOffsets.set(file, offsets);
    }
    // 行号沿用快照的 LF 索引，不能用 TS 对 Unicode 分隔符的语法行计数。
    const line = (position: number) => {
      let low = 0,
        high = offsets.length;
      while (low < high) {
        const middle = (low + high) >>> 1;
        if (offsets[middle] <= position) low = middle + 1;
        else high = middle;
      }
      return low;
    };
    return {
      snapshot_id: input.snapshot_id,
      file_path: file.fileName.slice(prefix.length),
      start_line: line(node.getStart(file)),
      end_line: line(Math.max(node.getStart(file), node.end - 1)),
    };
  }
  function diagnostic(code: string, message: string, node: ts.Node) {
    if (result.diagnostics.length >= MAX_ITEMS)
      throw new ParseFailure("result_limit");
    result.diagnostics.push({
      code,
      message,
      severity: "warning",
      source_ref: ref(node),
    });
  }
  for (const file of program.getSourceFiles()) {
    if (program.getSyntacticDiagnostics(file).length) {
      result.coverage.syntax_failed_files++;
      diagnostic(
        "FRONTEND_SYNTAX_ERROR",
        "文件语法无法解析，已保留其他文件的结果。",
        file,
      );
      continue;
    }
    result.coverage.parsed_files++;
    valid.add(file);
    const stack: ts.Node[] = [file];
    while (stack.length) {
      const node = stack.pop()!;
      nodes.push(node);
      if (nodes.length > MAX_NODES) throw new ParseFailure("ast_node_limit");
      const children: ts.Node[] = [];
      ts.forEachChild(node, (child) => {
        children.push(child);
      });
      for (let index = children.length - 1; index >= 0; index--)
        stack.push(children[index]);
    }
  }
  const id = (node: ts.Node, kind: string) =>
    createHash("sha256")
      .update(`${kind}:${node.getSourceFile().fileName}:${node.getStart()}`)
      .digest("hex");
  const functions = new Map<ts.Node, string>();
  const changed = new Set<ts.Symbol>();
  const symbolAt = (node: ts.Node) => checker.getSymbolAtLocation(node);
  function rootIdentifier(node: ts.Node): ts.Identifier | undefined {
    if (ts.isIdentifier(node)) return node;
    if (
      ts.isPropertyAccessExpression(node) ||
      ts.isElementAccessExpression(node)
    )
      return rootIdentifier(node.expression);
    return undefined;
  }
  for (const node of nodes) {
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind >= ts.SyntaxKind.FirstAssignment &&
      node.operatorToken.kind <= ts.SyntaxKind.LastAssignment
    ) {
      const root = rootIdentifier(node.left);
      const symbol = root && symbolAt(root);
      if (symbol) changed.add(symbol);
    }
    if (
      (ts.isPostfixUnaryExpression(node) || ts.isPrefixUnaryExpression(node)) &&
      (node.operator === ts.SyntaxKind.PlusPlusToken ||
        node.operator === ts.SyntaxKind.MinusMinusToken)
    ) {
      const root = rootIdentifier(node.operand);
      const symbol = root && symbolAt(root);
      if (symbol) changed.add(symbol);
    }
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      /\.(interceptors|defaults)\b/.test(node.expression.getText())
    ) {
      const root = rootIdentifier(node.expression);
      const symbol = root && symbolAt(root);
      if (symbol) changed.add(symbol);
    }
    if (isFunction(node) && node.body) {
      const parent = node.parent;
      const name =
        node.name?.getText() ??
        (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent)
          ? parent.name.getText()
          : `回调@${ref(node).start_line}`);
      functions.set(node, id(node, "function"));
      result.functions.push({
        id: id(node, "function"),
        name: name.slice(0, 200),
        source_ref: ref(node),
        entry_points: [],
      });
      if (result.functions.length > MAX_ITEMS)
        throw new ParseFailure("result_limit");
    }
    if (
      ts.isImportDeclaration(node) &&
      ts.isStringLiteral(node.moduleSpecifier) &&
      node.moduleSpecifier.text.startsWith(".") &&
      !resolve(node.moduleSpecifier.text, node.getSourceFile().fileName)
    ) {
      diagnostic(
        "UNRESOLVED_LOCAL_IMPORT",
        "本地导入不存在或有多个候选，未选择目标。",
        node,
      );
    }
  }
  function unwrap(node: ts.Expression): ts.Expression {
    while (
      ts.isParenthesizedExpression(node) ||
      ts.isAsExpression(node) ||
      ts.isTypeAssertionExpression(node) ||
      ts.isSatisfiesExpression(node)
    )
      node = node.expression;
    return node;
  }
  function declaration(node: ts.Node): ts.Declaration | undefined {
    let symbol = symbolAt(node);
    if (!symbol || changed.has(symbol)) return undefined;
    if (symbol.flags & ts.SymbolFlags.Alias)
      symbol = checker.getAliasedSymbol(symbol);
    if (changed.has(symbol) || symbol.declarations?.length !== 1)
      return undefined;
    const item = symbol.declarations[0];
    return valid.has(item.getSourceFile()) ? item : undefined;
  }
  function value(
    node: ts.Expression | undefined,
    seen = new Set<ts.Node>(),
  ): ts.Expression | undefined {
    if (!node || seen.size > 32) return undefined;
    node = unwrap(node);
    if (seen.has(node)) return undefined;
    seen.add(node);
    if (!ts.isIdentifier(node)) return node;
    const item = declaration(node);
    if (
      item &&
      ts.isVariableDeclaration(item) &&
      item.parent.flags & ts.NodeFlags.Const
    )
      return value(item.initializer, seen);
    return undefined;
  }
  function text(
    node: ts.Expression | undefined,
    depth = 0,
  ): string | undefined {
    if (depth > 32) return undefined;
    const item = value(node);
    if (!item) return undefined;
    if (ts.isStringLiteral(item) || ts.isNoSubstitutionTemplateLiteral(item))
      return item.text;
    if (ts.isTemplateExpression(item)) {
      let result = item.head.text;
      if (result.length > 8192) return undefined;
      for (const span of item.templateSpans) {
        const interpolation = text(span.expression, depth + 1);
        if (
          interpolation === undefined ||
          result.length + interpolation.length + span.literal.text.length > 8192
        )
          return undefined;
        result += interpolation + span.literal.text;
      }
      return result;
    }
    if (
      ts.isBinaryExpression(item) &&
      item.operatorToken.kind === ts.SyntaxKind.PlusToken
    ) {
      const left = text(item.left, depth + 1),
        right = text(item.right, depth + 1);
      if (
        left !== undefined &&
        right !== undefined &&
        left.length + right.length <= 8192
      )
        return left + right;
    }
    return undefined;
  }
  function properties(
    node: ts.Expression | undefined,
  ): Map<string, ts.Expression> | undefined {
    if (!node) return new Map();
    const item = value(node);
    if (!item || !ts.isObjectLiteralExpression(item)) return undefined;
    const values = new Map<string, ts.Expression>();
    for (const prop of item.properties) {
      if (
        (!ts.isPropertyAssignment(prop) &&
          !ts.isShorthandPropertyAssignment(prop)) ||
        ts.isComputedPropertyName(prop.name)
      )
        return undefined;
      const name =
        ts.isIdentifier(prop.name) || ts.isStringLiteral(prop.name)
          ? prop.name.text
          : prop.name.getText();
      if (values.has(name)) return undefined;
      values.set(
        name,
        ts.isShorthandPropertyAssignment(prop) ? prop.name : prop.initializer,
      );
    }
    return values;
  }
  function imported(
    node: ts.Node,
  ): { module: string; name: string } | undefined {
    const symbol = symbolAt(node);
    if (!symbol || changed.has(symbol) || symbol.declarations?.length !== 1)
      return undefined;
    const item = symbol.declarations[0];
    let owner: ts.Node | undefined = item;
    while (owner && !ts.isImportDeclaration(owner)) owner = owner.parent;
    if (!owner || !ts.isStringLiteral(owner.moduleSpecifier)) return undefined;
    const name = ts.isImportSpecifier(item)
      ? (item.propertyName ?? item.name).text
      : ts.isImportClause(item)
        ? "default"
        : "*";
    return { module: owner.moduleSpecifier.text, name };
  }
  function target(
    node: ts.Expression | undefined,
    seen = new Set<ts.Node>(),
  ): string | undefined {
    if (!node || seen.has(node) || seen.size > 32) return undefined;
    seen.add(node);
    node = unwrap(node);
    if (functions.has(node)) return functions.get(node);
    const item = declaration(node);
    if (item && functions.has(item)) return functions.get(item);
    if (
      item &&
      ts.isVariableDeclaration(item) &&
      item.parent.flags & ts.NodeFlags.Const &&
      item.initializer
    )
      return target(item.initializer, seen);
    return undefined;
  }
  function owner(node: ts.Node): string | null {
    let parent: ts.Node | undefined = node.parent;
    while (parent) {
      if (functions.has(parent)) return functions.get(parent)!;
      parent = parent.parent;
    }
    return null;
  }
  const evidence = (
    node: ts.Node,
    rule: string,
    kind: Evidence["kind"] = "source_fact",
  ): Evidence => ({ kind, rule, source_ref: ref(node) });
  const relationKeys = new Set<string>();
  function connect(
    source: string | null | undefined,
    targetId: string | undefined,
    relation: Result["relations"][number]["relation"],
    proof: Evidence,
  ) {
    if (!source || !targetId) return;
    const key = `${source}:${targetId}:${relation}:${JSON.stringify(proof)}`;
    if (relationKeys.has(key)) return;
    relationKeys.add(key);
    result.relations.push({
      source_id: source,
      target_id: targetId,
      relation,
      evidence: [proof],
    });
    if (result.relations.length > MAX_ITEMS)
      throw new ParseFailure("result_limit");
  }
  function axiosImport(node: ts.Node): boolean {
    const origin = imported(node);
    return origin?.module === "axios" && origin.name === "default";
  }
  function isFetch(node: ts.Expression, seen = new Set<ts.Node>()): boolean {
    node = unwrap(node);
    if (seen.has(node) || seen.size > 32) return false;
    seen.add(node);
    if (ts.isIdentifier(node) && node.text === "fetch" && !symbolAt(node))
      return true;
    const binding = declaration(node);
    return !!(
      binding &&
      ts.isVariableDeclaration(binding) &&
      binding.parent.flags & ts.NodeFlags.Const &&
      binding.initializer &&
      isFetch(binding.initializer, seen)
    );
  }
  function axiosClient(
    node: ts.Expression,
    seen = new Set<ts.Node>(),
  ):
    | {
        base: string | undefined;
        method: string | undefined;
        proof: ts.Node;
        canConfirm: boolean;
      }
    | undefined {
    if (seen.has(node) || seen.size > 32) return undefined;
    seen.add(node);
    if (axiosImport(node))
      return { base: "", method: "GET", proof: node, canConfirm: true };
    const binding = declaration(node);
    if (
      binding &&
      ts.isVariableDeclaration(binding) &&
      binding.parent.flags & ts.NodeFlags.Const &&
      binding.initializer &&
      ts.isIdentifier(binding.initializer)
    )
      return axiosClient(binding.initializer, seen);
    const item = value(node);
    if (
      item &&
      ts.isCallExpression(item) &&
      ts.isPropertyAccessExpression(item.expression) &&
      item.expression.name.text === "create" &&
      axiosImport(item.expression.expression)
    ) {
      const props = properties(item.arguments[0]);
      return {
        base:
          props && !hasCustomTransport(props)
            ? props.has("baseURL")
              ? text(props.get("baseURL"))
              : ""
            : undefined,
        method: props
          ? props.has("method")
            ? text(props.get("method"))
            : "GET"
          : undefined,
        proof: item,
        canConfirm: !!props && !hasCustomTransport(props),
      };
    }
    // 客户端配置被修改后仍保留请求位置，但不确认目标路径。
    const symbol = symbolAt(node);
    if (symbol?.declarations?.length === 1) {
      const d = symbol.declarations[0];
      if (
        ts.isImportClause(d) &&
        d.parent &&
        ts.isImportDeclaration(d.parent) &&
        ts.isStringLiteral(d.parent.moduleSpecifier) &&
        d.parent.moduleSpecifier.text === "axios"
      )
        return {
          base: undefined,
          method: undefined,
          proof: node,
          canConfirm: false,
        };
      if (
        ts.isVariableDeclaration(d) &&
        d.initializer &&
        ts.isCallExpression(d.initializer) &&
        ts.isPropertyAccessExpression(d.initializer.expression) &&
        d.initializer.expression.name.text === "create" &&
        axiosImport(d.initializer.expression.expression)
      )
        return {
          base: undefined,
          method: undefined,
          proof: d,
          canConfirm: false,
        };
    }
    return undefined;
  }
  function hasCustomTransport(config: Map<string, ts.Expression>): boolean {
    return [
      "adapter",
      "transport",
      "allowAbsoluteUrls",
      "transformRequest",
      "beforeRedirect",
      "proxy",
    ].some((key) => config.has(key));
  }
  function request(node: ts.CallExpression): RequestInfo | undefined {
    const expression = unwrap(node.expression);
    let url: string | undefined,
      method: string | undefined,
      base: string | undefined = "",
      proof: ts.Node = node;
    let library = "";
    if (isFetch(expression)) {
      library = "fetch";
      url = text(node.arguments[0]);
      const config = properties(node.arguments[1]);
      method = config
        ? config.has("method")
          ? text(config.get("method"))
          : "GET"
        : undefined;
    } else {
      const receiver = ts.isPropertyAccessExpression(expression)
        ? expression.expression
        : expression;
      const client = axiosClient(receiver);
      if (!client) return undefined;
      const member = ts.isPropertyAccessExpression(expression)
        ? expression.name.text
        : "request";
      if (member !== "request" && !METHODS.has(member.toUpperCase()))
        return undefined;
      library = "axios";
      base = client.base;
      proof = client.proof;
      const first = node.arguments[0];
      const objectCall =
        member === "request" &&
        value(first) &&
        ts.isObjectLiteralExpression(value(first)!);
      const configArg = objectCall
        ? first
        : node.arguments[["post", "put", "patch"].includes(member) ? 2 : 1];
      const config = properties(configArg);
      url = objectCall ? text(config?.get("url")) : text(first);
      method =
        member === "request"
          ? config
            ? config.has("method")
              ? text(config.get("method"))
              : client.method
            : undefined
          : member.toUpperCase();
      if (!config) base = undefined;
      else if (config.has("baseURL")) base = text(config.get("baseURL"));
      if (config?.has("method") && member !== "request")
        method = member.toUpperCase();
      if (!client.canConfirm || (config && hasCustomTransport(config)))
        base = undefined;
    }
    let resolution: RequestInfo["resolution"] = "static";
    let original: string | null = null,
      resolved: string | null = null;
    if (url === undefined || method === undefined) resolution = "dynamic";
    if (url !== undefined && !/[\x00-\x1f]/.test(url) && url.length <= 8192) {
      original = url.split(/[?#]/, 1)[0];
      if (/^(https?:)?\/\//.test(original)) {
        try {
          original = new URL(original, "https://example.invalid").pathname;
          resolved = original;
          resolution = "external";
        } catch {
          original = null;
          resolution = "unsupported";
        }
      } else if (base === undefined) {
        resolved = original;
        resolution = "unknown_base";
      } else if (base && /[?#\\]/.test(base)) {
        resolved = null;
        resolution = "unsupported";
      } else if (/^(https?:)?\/\//.test(base)) {
        try {
          resolved =
            new URL(base, "https://example.invalid").pathname.replace(
              /\/+$/,
              "",
            ) +
            "/" +
            original.replace(/^\/+/, "");
          resolution = "external";
        } catch {
          resolution = "unsupported";
        }
      } else {
        resolved = base
          ? base.split(/[?#]/, 1)[0].replace(/\/+$/, "") +
            "/" +
            original.replace(/^\/+/, "")
          : original;
        if (!resolved.startsWith("/") || resolved.startsWith("//"))
          resolution = "unknown_base";
        if (
          resolved.includes("\\") ||
          resolved.split("/").some((part) => part === "." || part === "..") ||
          /%2f|%5c|%2e/i.test(resolved)
        )
          resolution = "unsupported";
      }
    } else if (url !== undefined) resolution = "unsupported";
    const normalizedMethod = method?.toUpperCase();
    if (!normalizedMethod || !METHODS.has(normalizedMethod))
      resolution = "dynamic";
    const item: RequestInfo = {
      id: id(node, "request"),
      owner_id: owner(node),
      method:
        normalizedMethod && METHODS.has(normalizedMethod)
          ? normalizedMethod
          : null,
      original_path: original,
      path: resolved,
      resolution,
      source_ref: ref(node),
      evidence: [
        evidence(node, `${library}.request`),
        evidence(proof, `${library}.static_configuration`, "static_inference"),
      ],
    };
    if (resolution !== "static")
      diagnostic(
        `REQUEST_${resolution.toUpperCase()}`,
        "请求目标无法静态确认，请查看源码、候选及路径限制。",
        node,
      );
    return item;
  }
  // 配置对象逃逸或经别名修改后，不再把初始化字面量视为固定配置。
  const aliases = new Map<ts.Symbol, Set<ts.Symbol>>();
  for (const node of nodes) {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer &&
      ts.isIdentifier(node.initializer)
    ) {
      const left = symbolAt(node.name),
        right = symbolAt(node.initializer);
      if (left && right) {
        if (!aliases.has(left)) aliases.set(left, new Set());
        if (!aliases.has(right)) aliases.set(right, new Set());
        aliases.get(left)!.add(right);
        aliases.get(right)!.add(left);
      }
    }
    if (ts.isCallExpression(node)) {
      const call = unwrap(node.expression);
      const receiver = ts.isPropertyAccessExpression(call)
        ? call.expression
        : call;
      const known =
        isFetch(call) ||
        axiosClient(receiver) ||
        (ts.isPropertyAccessExpression(call) &&
          call.name.text === "create" &&
          axiosImport(receiver));
      if (!known)
        for (const argument of node.arguments) {
          if (ts.isIdentifier(argument)) {
            const resolved = value(argument),
              symbol = symbolAt(argument);
            if (
              symbol &&
              ((resolved && ts.isObjectLiteralExpression(resolved)) ||
                axiosClient(argument))
            )
              changed.add(symbol);
          }
        }
    }
  }
  const pendingChanges = [...changed];
  for (let index = 0; index < pendingChanges.length; index++)
    for (const alias of aliases.get(pendingChanges[index]) ?? []) {
      if (!changed.has(alias)) {
        changed.add(alias);
        pendingChanges.push(alias);
      }
    }
  for (const node of nodes) {
    if (functions.has(node))
      connect(
        owner(node),
        functions.get(node),
        "contains_function",
        evidence(node, "javascript.lexical_containment"),
      );
    if (ts.isCallExpression(node)) {
      connect(
        owner(node),
        target(node.expression),
        "direct_call",
        evidence(node, "javascript.direct_call"),
      );
      const item = request(node);
      if (item) {
        result.requests.push(item);
        if (result.requests.length > MAX_ITEMS)
          throw new ParseFailure("result_limit");
        connect(
          item.owner_id,
          item.id,
          "contains_request",
          evidence(node, "javascript.lexical_request"),
        );
      }
      if (
        ts.isPropertyAccessExpression(node.expression) &&
        ["mutate", "mutateAsync"].includes(node.expression.name.text)
      ) {
        const initializer = value(node.expression.expression);
        if (
          initializer &&
          ts.isCallExpression(initializer) &&
          imported(initializer.expression)?.module ===
            "@tanstack/react-query" &&
          imported(initializer.expression)?.name === "useMutation"
        ) {
          connect(
            owner(node),
            target(properties(initializer.arguments[0])?.get("mutationFn")),
            "callback_binding",
            evidence(node, "tanstack-query/5.mutation_fn", "framework_rule"),
          );
        }
      }
    }
    if (
      ts.isJsxAttribute(node) &&
      node.initializer &&
      ts.isJsxExpression(node.initializer) &&
      node.initializer.expression
    ) {
      const element = node.parent.parent;
      if (
        !ts.isJsxOpeningElement(element) &&
        !ts.isJsxSelfClosingElement(element)
      )
        continue;
      const tag = element.tagName;
      const attribute = node.name.getText();
      let rule: string | undefined;
      if (
        ts.isIdentifier(tag) &&
        imported(tag)?.module === "antd" &&
        imported(tag)?.name === "Form" &&
        attribute === "onFinish"
      )
        rule = "antd/6.form_on_finish";
      if (
        ts.isIdentifier(tag) &&
        /^[a-z]/.test(tag.text) &&
        ["onClick", "onSubmit", "onChange"].includes(attribute)
      )
        rule = "react/19.dom_event";
      const targetId = target(node.initializer.expression);
      const fn = result.functions.find((fn) => fn.id === targetId);
      const attributes = element.attributes.properties;
      const overridden = attributes.some(
        (item, index) =>
          (ts.isJsxSpreadAttribute(item) && index > attributes.indexOf(node)) ||
          (ts.isJsxAttribute(item) &&
            item !== node &&
            item.name.getText() === attribute),
      );
      if (rule && overridden)
        diagnostic(
          "JSX_BINDING_DYNAMIC",
          "事件属性重复或可能被展开属性覆盖，未确认入口。",
          node,
        );
      else if (rule && fn)
        fn.entry_points.push(evidence(node, rule, "framework_rule"));
    }
  }
  result.coverage.function_count = result.functions.length;
  result.coverage.request_count = result.requests.length;
  result.coverage.complete = result.diagnostics.length === 0;
  return result;
}
