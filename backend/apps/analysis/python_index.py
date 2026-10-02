import ast
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from apps.analysis.types import (
    MAX_AST_NODES,
    MAX_RESULTS,
    AnalysisFailed,
    Diagnostic,
    Source,
    SourceRef,
    Symbol,
)

type Definition = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else None
    if isinstance(node, ast.Subscript):
        return dotted(node.value)
    return None


def literal_string(node: ast.AST | None) -> str | None:
    return (
        node.value
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        else None
    )


def assignment(node: ast.AST) -> tuple[str, ast.expr] | None:
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, node.value
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    ):
        return node.target.id, node.value
    return None


@dataclass
class Unit:
    path: str
    tree: ast.Module
    imports: dict[str, str] = field(default_factory=dict)
    definitions: dict[str, Definition] = field(default_factory=dict)
    values: dict[str, ast.expr] = field(default_factory=dict)
    blocked: set[str] = field(default_factory=set)


class PythonIndex:
    def __init__(self, snapshot_id: str, sources: list[Source]) -> None:
        self.snapshot_id = snapshot_id
        self.units: dict[str, Unit] = {}
        self.modules: dict[str, list[Unit]] = {}
        self.diagnostics: list[Diagnostic] = []
        self.syntax_failed = 0
        budget = 0
        for source in sources:
            if not source.file_path.endswith(".py"):
                continue
            try:
                tree = ast.parse(source.content, filename="<snapshot>")
            except SyntaxError as exc:
                self.syntax_failed += 1
                line = min(
                    max(exc.lineno or 1, 1), max(1, len(source.content.splitlines()))
                )
                self.diagnostics.append(
                    {
                        "code": "PYTHON_SYNTAX_ERROR",
                        "message": "此文件存在 Python 语法错误，未参与规则识别。",
                        "severity": "warning",
                        "source_ref": {
                            "snapshot_id": snapshot_id,
                            "file_path": source.file_path,
                            "start_line": line,
                            "end_line": line,
                        },
                    }
                )
                continue
            except (ValueError, RecursionError, MemoryError):
                raise AnalysisFailed("ast_resource_limit") from None
            for _ in ast.walk(tree):
                budget += 1
                if budget > MAX_AST_NODES:
                    raise AnalysisFailed("ast_node_limit")
            unit = Unit(source.file_path, tree)
            self.units[unit.path] = unit
            parts = list(PurePosixPath(unit.path).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            for offset in range(len(parts)):
                self.modules.setdefault(".".join(parts[offset:]), []).append(unit)
            self._index(unit)

    def ref(self, unit: Unit, node: ast.AST) -> SourceRef:
        start = int(getattr(node, "lineno", 1))
        return {
            "snapshot_id": self.snapshot_id,
            "file_path": unit.path,
            "start_line": start,
            "end_line": int(getattr(node, "end_lineno", None) or start),
        }

    def symbol(self, unit: Unit, node: Definition) -> Symbol:
        return {"name": node.name, "source_ref": self.ref(unit, node)}

    def warn(self, code: str, message: str, unit: Unit, node: ast.AST) -> None:
        diagnostic: Diagnostic = {
            "code": code,
            "message": message,
            "severity": "warning",
            "source_ref": self.ref(unit, node),
        }
        if diagnostic not in self.diagnostics:
            self.diagnostics.append(diagnostic)
        if len(self.diagnostics) > MAX_RESULTS:
            raise AnalysisFailed("diagnostic_limit")

    def _index(self, unit: Unit) -> None:
        seen: set[str] = set()
        for node in unit.tree.body:
            bindings: dict[str, str] = {}
            if isinstance(node, ast.Import):
                bindings = {
                    alias.asname or alias.name.split(".")[0]: alias.name
                    if alias.asname
                    else alias.name.split(".")[0]
                    for alias in node.names
                }
            elif isinstance(node, ast.ImportFrom):
                module = "." * node.level + (node.module or "")
                for alias in node.names:
                    if alias.name == "*":
                        self.warn(
                            "WILDCARD_IMPORT",
                            "星号导入不能用于确定名称归属。",
                            unit,
                            node,
                        )
                        continue
                    bindings[alias.asname or alias.name] = (
                        module + ("" if module.endswith(".") else ".") + alias.name
                    )
            elif isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                unit.definitions[node.name] = node
                bindings[node.name] = ""
            elif (pair := assignment(node)) is not None:
                unit.values[pair[0]] = pair[1]
                bindings[pair[0]] = ""
            else:
                # 条件定义、重复赋值和运行期写入不能当作唯一静态绑定。
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                        unit.blocked.add(child.id)
                    elif isinstance(child, ast.Attribute) and isinstance(
                        child.ctx, (ast.Store, ast.Del)
                    ):
                        root_name = dotted(child)
                        if root_name:
                            unit.blocked.add(root_name.split(".")[0])
                    elif isinstance(
                        child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                    ):
                        unit.blocked.add(child.name)
            for name, target in bindings.items():
                if name in seen:
                    unit.blocked.add(name)
                seen.add(name)
                if target:
                    unit.imports[name] = target

    def name(self, unit: Unit, node: ast.AST) -> str | None:
        name = dotted(node)
        if not name or name.split(".")[0] in unit.blocked:
            return None
        first, _, tail = name.partition(".")
        target = unit.imports.get(first, first)
        if target.split(".")[0] in {"django", "rest_framework"}:
            parts = target.split(".")
            if any(
                ".".join(parts[:length]) in self.modules
                for length in range(1, len(parts) + 1)
            ):
                return None
        return target + ("." + tail if tail else "")

    def module(self, name: str, origin: Unit) -> Unit | None:
        if name.startswith("."):
            level = len(name) - len(name.lstrip("."))
            parent = PurePosixPath(origin.path).parent
            for _ in range(level - 1):
                parent = parent.parent
            relative = parent.joinpath(*name[level:].split("."))
            candidates = [
                self.units[p]
                for p in (str(relative) + ".py", str(relative / "__init__.py"))
                if p in self.units
            ]
        else:
            candidates = self.modules.get(name, [])
        return candidates[0] if len(candidates) == 1 else None

    def resolve(
        self, unit: Unit, node: ast.AST, seen: frozenset[tuple[str, str]] = frozenset()
    ) -> tuple[Unit, Definition] | None:
        name = self.name(unit, node)
        if name is None or (unit.path, name) in seen or len(seen) >= 32:
            return None
        if name in unit.definitions and name not in unit.imports:
            return unit, unit.definitions[name]
        if name in unit.values:
            return self.resolve(unit, unit.values[name], seen | {(unit.path, name)})
        module_name, _, symbol = name.rpartition(".")
        other = self.module(module_name or ".", unit)
        if other:
            return self.resolve(other, ast.Name(id=symbol), seen | {(unit.path, name)})
        return None
