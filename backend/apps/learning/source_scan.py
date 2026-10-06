"""从快照文本收集有界知识事实；不导入用户模块或访问依赖源。"""

import ast
import json
import re
import sys
import tomllib
from pathlib import PurePosixPath
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement

from apps.analysis.types import MAX_AST_NODES, Source

type ScopeBindings = tuple[int, int, dict[str, str], set[str]]

KNOWLEDGE_RULE_VERSION = "source-knowledge/1.0.0"
CARD_VERSION = "1.1.0"
MAX_FACTS = 10_000
MAX_DECLARATIONS = 2_000
MAX_KNOWLEDGE_BYTES = 2 * 1024 * 1024
PACKAGE_MAP = {
    "django": ("django", "django-framework"),
    "rest_framework": ("djangorestframework", "drf-framework"),
    "requests": ("requests", "requests-client"),
    "httpx": ("httpx", "httpx-client"),
}
STDLIB_CARDS = {
    "asyncio": "asyncio-library",
    "dataclasses": "dataclasses-library",
    "contextlib": "contextlib-library",
    "functools": "functools-library",
    "collections": "collections-library",
}
MANIFEST_NAME = re.compile(r"requirements(?:[-_.][A-Za-z0-9_-]+)?\.txt\Z")


def is_manifest(path: str) -> bool:
    name = PurePosixPath(path).name
    return name == "pyproject.toml" or MANIFEST_NAME.fullmatch(name) is not None


def _ref(snapshot_id: str, source: Source, node: ast.AST | int) -> dict[str, Any]:
    start = node if isinstance(node, int) else getattr(node, "lineno", 1)
    end = start if isinstance(node, int) else getattr(node, "end_lineno", start)
    return {
        "snapshot_id": snapshot_id,
        "file_path": source.file_path,
        "start_line": start,
        "end_line": end or start,
    }


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _bindings(
    body: list[ast.stmt], arguments: ast.arguments | None = None
) -> tuple[dict[str, str], set[str]]:
    aliases: dict[str, str] = {}
    blocked: set[str] = set()
    if arguments is not None:
        blocked.update(
            arg.arg
            for arg in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
        )
        blocked.update(
            arg.arg for arg in (arguments.vararg, arguments.kwarg) if arg is not None
        )

    def visit(node: ast.AST) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name in aliases:
                    blocked.add(name)
                aliases[name] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                for alias in node.names:
                    if alias.name != "*":
                        name = alias.asname or alias.name
                        if name in aliases:
                            blocked.add(name)
                        aliases[name] = f"{node.module}.{alias.name}"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            blocked.add(node.name)
        elif isinstance(node, ast.Lambda):
            return
        elif isinstance(
            node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
        ):
            for child in ast.walk(node):
                if isinstance(child, ast.NamedExpr):
                    visit(child.target)
        else:
            if isinstance(node, ast.Name) and isinstance(
                node.ctx, (ast.Store, ast.Del)
            ):
                blocked.add(node.id)
            for child in ast.iter_child_nodes(node):
                visit(child)

    for node in body:
        visit(node)
    return aliases, blocked


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def scan_knowledge_facts(snapshot_id: str, sources: list[Source]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    packages: dict[str, dict[str, Any]] = {}
    declarations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    trees: dict[str, ast.Module] = {}
    modules: dict[str, set[str]] = {}
    truncated = False
    syntax_failed = 0
    budget = 0
    package_ref_count = 0
    seen_hits: set[tuple[str, str, int, int]] = set()
    seen_package_refs: set[tuple[str, str, str, str, int, int]] = set()
    decorator_owners: dict[tuple[str, int, int], dict[str, Any]] = {}
    python_paths = {
        source.file_path for source in sources if source.file_path.endswith(".py")
    }
    for path in python_paths:
        parts = list(PurePosixPath(path).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        for offset in range(len(parts)):
            modules.setdefault(".".join(parts[offset:]), set()).add(path)

    def warn(code: str, message: str, ref: dict[str, Any] | None) -> None:
        nonlocal truncated
        if len(diagnostics) < 100:
            diagnostics.append(
                {
                    "code": code,
                    "message": message,
                    "severity": "warning",
                    "source_ref": ref,
                }
            )
        else:
            truncated = True

    def hit(slug: str, rule: str, ref: dict[str, Any]) -> None:
        nonlocal truncated
        key = (slug, ref["file_path"], ref["start_line"], ref["end_line"])
        if key in seen_hits:
            return
        if len(hits) >= MAX_FACTS:
            truncated = True
            return
        seen_hits.add(key)
        hits.append(
            {
                "concept_key": slug,
                "card_slug": slug,
                "card_version": CARD_VERSION,
                "rule_id": rule,
                "source_ref": ref,
            }
        )

    def declaration(raw: str, source: Source, line: int) -> None:
        nonlocal truncated
        ref = _ref(snapshot_id, source, line)
        if len(declarations) >= MAX_DECLARATIONS:
            truncated = True
            return
        try:
            item = Requirement(raw)
        except InvalidRequirement:
            warn("DEPENDENCY_DECLARATION_UNSUPPORTED", "依赖声明未能静态解析。", ref)
            return
        # URL、索引配置和认证信息不进入持久化事实或模型预览。
        value = {
            "distribution": _normalized(item.name),
            "specifier": str(item.specifier),
            "conditional": item.marker is not None,
            "optional": False,
            "source_ref": ref,
        }
        declarations.append(value)
        if item.url:
            warn(
                "DEPENDENCY_URL_NOT_FOLLOWED",
                "仅记录依赖名称，不读取或保存声明中的外部地址。",
                ref,
            )

    for source in sources:
        path = source.file_path
        if path.endswith(".py"):
            try:
                tree = ast.parse(source.content, filename="<snapshot>")
            except (SyntaxError, ValueError, RecursionError):
                syntax_failed += 1
                warn(
                    "KNOWLEDGE_SYNTAX_ERROR",
                    "此文件语法不可解析，未识别其知识点。",
                    _ref(snapshot_id, source, 1),
                )
                continue
            size = sum(1 for _ in ast.walk(tree))
            budget += size
            if budget > MAX_AST_NODES:
                truncated = True
                warn(
                    "KNOWLEDGE_AST_LIMIT",
                    "知识扫描达到语法节点上限，保留此前事实。",
                    None,
                )
                break
            trees[path] = tree
        elif is_manifest(path):
            lines = source.content.splitlines()
            if PurePosixPath(path).name == "pyproject.toml":
                try:
                    document = tomllib.loads(source.content)
                except (tomllib.TOMLDecodeError, ValueError):
                    warn(
                        "DEPENDENCY_MANIFEST_INVALID",
                        "依赖清单结构无效，未解析声明。",
                        _ref(snapshot_id, source, 1),
                    )
                    continue
                project = document.get("project", {})
                if not isinstance(project, dict):
                    warn(
                        "DEPENDENCY_MANIFEST_INVALID",
                        "依赖清单 project 字段结构无效。",
                        _ref(snapshot_id, source, 1),
                    )
                    continue
                groups = [(project.get("dependencies", []), False)]
                optional = project.get("optional-dependencies", {})
                if isinstance(optional, dict):
                    groups.extend((items, True) for items in optional.values())
                for items, is_optional in groups:
                    if not isinstance(items, list):
                        warn(
                            "DEPENDENCY_MANIFEST_INVALID",
                            "依赖组必须是字符串列表。",
                            _ref(snapshot_id, source, 1),
                        )
                        continue
                    for raw in items:
                        if not isinstance(raw, str):
                            warn(
                                "DEPENDENCY_MANIFEST_INVALID",
                                "依赖声明必须是字符串。",
                                _ref(snapshot_id, source, 1),
                            )
                            continue
                        candidates = [
                            n for n, text in enumerate(lines, 1) if raw in text
                        ]
                        if len(candidates) != 1:
                            warn(
                                "DEPENDENCY_REFERENCE_AMBIGUOUS",
                                "依赖声明来源行无法唯一定位，未建立引用。",
                                _ref(snapshot_id, source, 1),
                            )
                            continue
                        before = len(declarations)
                        declaration(raw, source, candidates[0])
                        if len(declarations) > before:
                            declarations[-1]["optional"] = is_optional
            else:
                for line, raw in enumerate(lines, 1):
                    raw = raw.strip()
                    if not raw or raw.startswith("#"):
                        continue
                    if raw.startswith("-") or raw.endswith("\\"):
                        warn(
                            "DEPENDENCY_DIRECTIVE_UNSUPPORTED",
                            "依赖选项或续行未执行，仅支持静态独立声明。",
                            _ref(snapshot_id, source, line),
                        )
                        continue
                    declaration(raw.split(" #", 1)[0], source, line)

    declared = {item["distribution"] for item in declarations}
    declaration_groups: dict[str, list[dict[str, Any]]] = {}
    for item in declarations:
        declaration_groups.setdefault(item["distribution"], []).append(item)
    stdlib = sys.stdlib_module_names

    def classify(module: str, level: int, source: Source) -> tuple[str, str | None]:
        root = module.split(".", 1)[0]
        if level:
            parent = PurePosixPath(source.file_path).parent
            for _ in range(level - 1):
                parent = parent.parent
            target = parent.joinpath(*module.split(".")) if module else parent
            candidates = {
                str(target) + ".py",
                str(target / "__init__.py"),
            } & python_paths
            return ("local", None) if len(candidates) == 1 else ("unknown", None)
        local = modules.get(module, set()) or modules.get(root, set())
        if local:
            if len(local) == 1 and root not in stdlib:
                return "local", None
            return "unknown", None
        if root in stdlib:
            return "stdlib", None
        if root in PACKAGE_MAP:
            return "third_party", PACKAGE_MAP[root][0]
        if _normalized(root) in declared:
            return "third_party", _normalized(root)
        return "unknown", None

    def package_ref(
        name: str,
        kind: str,
        distribution: str | None,
        ref: dict[str, Any],
        *,
        usage: bool = False,
    ) -> None:
        nonlocal truncated, package_ref_count
        key = f"{kind}:{name}"
        field = "usage_refs" if usage else "source_refs"
        identity = (
            kind,
            name,
            field,
            ref["file_path"],
            ref["start_line"],
            ref["end_line"],
        )
        if identity in seen_package_refs:
            return
        if package_ref_count >= MAX_FACTS or (
            key not in packages and len(packages) >= MAX_FACTS
        ):
            truncated = True
            return
        if key not in packages:
            matching = declaration_groups.get(distribution, []) if distribution else []
            if len(matching) > 20:
                truncated = True
            packages[key] = {
                "name": name,
                "kind": kind,
                "distribution": distribution,
                "declarations": matching[:20],
                "declaration_count": len(matching),
                "source_refs": [],
                "usage_refs": [],
            }
        packages[key][field].append(ref)
        seen_package_refs.add(identity)
        package_ref_count += 1

    for source in sources:
        current_tree = trees.get(source.file_path)
        if current_tree is None:
            continue
        global_aliases, global_blocked = _bindings(current_tree.body)
        scopes = [
            (
                node.body[0].lineno,
                node.end_lineno or node.lineno,
                *_bindings(
                    node.body,
                    node.args
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    else None,
                ),
            )
            for node in ast.walk(current_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.body
        ]
        expression_shadows: set[int] = set()
        for node in ast.walk(current_tree):
            names: set[str] = set()
            if isinstance(node, ast.Lambda):
                _, names = _bindings([], node.args)
            elif isinstance(
                node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
            ):
                names = {
                    child.id
                    for generator in node.generators
                    for child in ast.walk(generator.target)
                    if isinstance(child, ast.Name)
                }
            if names:
                expression_shadows.update(
                    id(child)
                    for child in ast.walk(node)
                    if (name := _dotted(child)) is not None
                    and name.split(".", 1)[0] in names
                )
        events: dict[int, list[tuple[bool, int]]] = {}
        for index, scope in enumerate(scopes):
            events.setdefault(scope[0], []).append((True, index))
            events.setdefault(scope[1] + 1, []).append((False, index))
        active_scopes: set[int] = set()
        scope_lines: dict[int, list[ScopeBindings]] = {}
        ordered: list[ScopeBindings] = []
        for line in range(1, len(source.content.splitlines()) + 1):
            if line in events:
                for entering, index in events[line]:
                    if entering:
                        active_scopes.add(index)
                    else:
                        active_scopes.discard(index)
                ordered = sorted(
                    (scopes[index] for index in active_scopes),
                    key=lambda scope: scope[1] - scope[0],
                )
            if ordered:
                scope_lines[line] = ordered

        def canonical(node: ast.AST) -> str | None:
            if id(node) in expression_shadows:
                return None
            name = _dotted(node)
            if name is None:
                return None
            root, _, tail = name.partition(".")
            line = getattr(node, "lineno", 0)
            for _, _, aliases, blocked in scope_lines.get(line, []):
                if root in blocked:
                    return None
                if root in aliases:
                    return aliases[root] + ("." + tail if tail else "")
            if root in global_blocked or root not in global_aliases:
                return None
            return global_aliases[root] + ("." + tail if tail else "")

        for node in ast.walk(current_tree):
            ref = _ref(snapshot_id, source, node)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    owner = _ref(snapshot_id, source, node)
                    if isinstance(node, ast.ClassDef):
                        owner["end_line"] = owner["start_line"]
                    for child in ast.walk(decorator):
                        if hasattr(child, "lineno"):
                            position = _ref(snapshot_id, source, child)
                            decorator_owners[
                                (
                                    source.file_path,
                                    position["start_line"],
                                    position["end_line"],
                                )
                            ] = owner
                    hit(
                        "python-decorators",
                        "python.decorator",
                        _ref(snapshot_id, source, decorator),
                    )
            if isinstance(node, (ast.With, ast.AsyncWith)):
                hit("python-context-managers", "python.context_manager", ref)
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
                hit("python-comprehensions", "python.comprehension", ref)
            if isinstance(node, (ast.GeneratorExp, ast.Yield, ast.YieldFrom)):
                hit("python-generators", "python.generator", ref)
            if isinstance(
                node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)
            ):
                hit("python-async", "python.async", ref)
            if isinstance(node, (ast.Try, ast.TryStar, ast.Raise)):
                hit("python-exceptions", "python.exception", ref)
            if isinstance(node, ast.Match):
                hit("python-pattern-matching", "python.match", ref)
            if isinstance(node, ast.AnnAssign) or (
                isinstance(node, ast.arg) and node.annotation is not None
            ):
                hit("python-type-annotations", "python.annotation", ref)
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.returns is not None
            ):
                hit(
                    "python-type-annotations",
                    "python.return_annotation",
                    _ref(snapshot_id, source, node.returns),
                )
            qualified = canonical(node)
            if qualified is not None:
                root = qualified.split(".", 1)[0]
                kind, distribution = classify(root, 0, source)
                package_ref(root, kind, distribution, ref, usage=True)
                if kind == "third_party" and root in PACKAGE_MAP:
                    hit(PACKAGE_MAP[root][1], "python.known_package_use", ref)
                    if qualified.startswith("rest_framework.serializers."):
                        hit("drf-serializers", "drf.serializer_api", ref)
                    if qualified.startswith(
                        (
                            "rest_framework.views.",
                            "rest_framework.viewsets.",
                            "rest_framework.generics.",
                            "rest_framework.decorators.",
                        )
                    ):
                        hit("drf-views", "drf.view_api", ref)
                    if qualified.startswith("django.db.models."):
                        hit("django-orm", "django.model_api", ref)
                    if qualified in {
                        "django.urls.path",
                        "django.urls.re_path",
                        "django.urls.include",
                    }:
                        hit("django-url-routing", "django.url_api", ref)
                elif kind == "stdlib" and root in STDLIB_CARDS:
                    hit(STDLIB_CARDS[root], "python.stdlib_use", ref)
            imports: list[tuple[str, int]] = []
            if isinstance(node, ast.Import):
                imports = [(alias.name, 0) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [(node.module or "", node.level)]
            for module, level in imports:
                name = ("." * level + module) if level else module.split(".", 1)[0]
                kind, distribution = classify(module, level, source)
                package_ref(name, kind, distribution, ref)
                root = module.split(".", 1)[0]
                if kind == "third_party" and root in PACKAGE_MAP:
                    hit(PACKAGE_MAP[root][1], "python.known_package_import", ref)
                elif kind == "stdlib" and root in STDLIB_CARDS:
                    hit(STDLIB_CARDS[root], "python.stdlib_import", ref)

    for item in hits:
        position = item["source_ref"]
        linked_owner = decorator_owners.get(
            (position["file_path"], position["start_line"], position["end_line"])
        )
        if linked_owner is not None:
            item["owner_ref"] = linked_owner
    hits.sort(
        key=lambda item: (
            item["concept_key"],
            item["source_ref"]["file_path"],
            item["source_ref"]["start_line"],
            item["source_ref"]["end_line"],
        )
    )
    result: dict[str, Any] = {
        "rule_version": KNOWLEDGE_RULE_VERSION,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "hits": hits,
        "packages": sorted(
            packages.values(), key=lambda item: (item["kind"], item["name"])
        ),
        "declarations": declarations,
        "diagnostics": diagnostics,
        "coverage": {
            "python_files": sum(source.file_path.endswith(".py") for source in sources),
            "parsed_files": len(trees),
            "syntax_failed_files": syntax_failed,
            "hit_count": len(hits),
            "package_count": len(packages),
            "complete": not diagnostics and not truncated,
            "truncated": truncated,
        },
    }

    def encoded_size() -> int:
        return len(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )

    if encoded_size() > MAX_KNOWLEDGE_BYTES:
        warn(
            "KNOWLEDGE_OUTPUT_LIMIT",
            "知识结果达到字节上限，部分事实未纳入；可按文件查看已保存命中。",
            None,
        )
        result["coverage"]["complete"] = False
        result["coverage"]["truncated"] = True
        # 同步缩减三类事实，保持顺序与引用完整；不输出残缺的单个事实。
        while encoded_size() > MAX_KNOWLEDGE_BYTES and any(
            result[key] for key in ("hits", "packages", "declarations")
        ):
            for key in ("hits", "packages", "declarations"):
                result[key] = result[key][: len(result[key]) // 2]
        result["coverage"]["hit_count"] = len(result["hits"])
        result["coverage"]["package_count"] = len(result["packages"])
    return result
