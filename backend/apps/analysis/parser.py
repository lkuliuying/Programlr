import ast
import re

from apps.analysis.actions import router_actions
from apps.analysis.drf_rules import HTTP_METHODS, ClassInfo, DrfRules
from apps.analysis.python_index import PythonIndex, Unit, dotted, literal_string
from apps.analysis.types import (
    MAX_RESULTS,
    RULE_VERSION,
    AnalysisFailed,
    AnalysisResult,
    Endpoint,
    Evidence,
    Source,
)

ROUTER_ACTIONS = {
    "list": ("GET", False),
    "create": ("POST", False),
    "retrieve": ("GET", True),
    "update": ("PUT", True),
    "partial_update": ("PATCH", True),
    "destroy": ("DELETE", True),
}
LIMITATIONS = [
    "仅静态规则结果，不是实际执行轨迹；不执行任何导入源码。",
    "字面量 path/include、直接 as_view、标准 Router 及字面量 action；动态分派与装饰参数保留诊断。",
    "Router 规则依据 DRF 3.18.1；框架版本未从导入项目运行环境验证。",
    "正则路由保留正则语义；HEAD/OPTIONS、DefaultRouter 根视图和格式后缀属于框架推导。",
    "不建立前端关联或通用调用图；外部包、复杂继承及运行时属性修改不自动补全。",
]


CONVERTERS = {
    "str": "[^/]+",
    "int": "[0-9]+",
    "slug": "[-a-zA-Z0-9_]+",
    "uuid": "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "path": ".+",
}


def path_regex(path: str) -> str | None:
    parts: list[str] = []
    offset = 0
    for match in re.finditer(r"<(?:(\w+):)?(\w+)>", path):
        converter, name = match.groups()
        if (converter or "str") not in CONVERTERS:
            return None
        parts.extend(
            [
                re.escape(path[offset : match.start()]),
                f"(?P<{name}>{CONVERTERS[converter or 'str']})",
            ]
        )
        offset = match.end()
    parts.append(re.escape(path[offset:]))
    return "".join(parts)


class RouteParser:
    def __init__(self, index: PythonIndex) -> None:
        self.index = index
        self.rules = DrfRules(index)
        self.endpoints: list[Endpoint] = []

    def evidence(
        self, unit: Unit, node: ast.AST, rule: str = "django.path"
    ) -> Evidence:
        return {
            "kind": "source_fact",
            "rule": rule,
            "source_ref": self.index.ref(unit, node),
        }

    def add(self, endpoint: Endpoint) -> None:
        if len(self.endpoints) >= MAX_RESULTS:
            raise AnalysisFailed("endpoint_limit")
        self.endpoints.append(endpoint)

    def walk(
        self,
        unit: Unit,
        expr: ast.AST,
        prefix: str,
        evidence: list[Evidence],
        seen: frozenset[tuple[str, str]] = frozenset(),
    ) -> None:
        if len(seen) >= 64 or len(prefix) > 2048:
            self.index.warn("ROUTE_LIMIT", "路由包含深度或路径长度超限。", unit, expr)
            return
        if isinstance(expr, (ast.List, ast.Tuple)):
            for item in expr.elts:
                self.walk(unit, item, prefix, evidence, seen)
            return
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            self.walk(unit, expr.left, prefix, evidence, seen)
            self.walk(unit, expr.right, prefix, evidence, seen)
            return
        if isinstance(expr, (ast.Name, ast.Attribute)):
            name = dotted(expr) or ""
            key = (unit.path, name)
            if key in seen:
                self.index.warn(
                    "ROUTE_CYCLE",
                    "路由包含或变量引用形成循环，已停止该分支。",
                    unit,
                    expr,
                )
                return
            if (
                isinstance(expr, ast.Attribute)
                and expr.attr == "urls"
                and isinstance(expr.value, ast.Name)
            ):
                self.router(unit, expr.value.id, prefix, evidence, expr)
                return
            if name in unit.values and name not in unit.blocked:
                self.walk(unit, unit.values[name], prefix, evidence, seen | {key})
                return
            imported = self.index.name(unit, expr)
            if imported:
                module_name, _, symbol = imported.rpartition(".")
                other = self.index.module(module_name, unit)
                if other and symbol in other.values and symbol not in other.blocked:
                    self.walk(
                        other, ast.Name(id=symbol), prefix, evidence, seen | {key}
                    )
                    return
        if (
            isinstance(expr, ast.Call)
            and self.index.name(unit, expr.func) == "django.urls.path"
        ):
            if (
                len(expr.args) < 2
                or len(expr.args) > 4
                or any(k.arg not in {"name", "kwargs"} for k in expr.keywords)
            ):
                self.index.warn(
                    "DYNAMIC_ROUTE", "path 的参数形状超出支持范围。", unit, expr
                )
                return
            part = literal_string(expr.args[0])
            if part is None or len(part) > 1024 or any(ord(x) < 32 for x in part):
                self.index.warn(
                    "DYNAMIC_ROUTE", "路由路径不是受支持的静态字符串。", unit, expr
                )
                return
            target = expr.args[1]
            chain = evidence + [self.evidence(unit, expr)]
            if (
                isinstance(target, ast.Call)
                and self.index.name(unit, target.func) == "django.urls.include"
            ):
                if not target.args:
                    self.index.warn(
                        "DYNAMIC_INCLUDE", "include 未提供静态目标。", unit, target
                    )
                    return
                value = target.args[0]
                module = literal_string(value)
                if module is not None:
                    other = self.index.module(module, unit)
                    if other:
                        self.walk(
                            other,
                            ast.Name(id="urlpatterns"),
                            prefix + part,
                            chain,
                            seen,
                        )
                    else:
                        self.index.warn(
                            "INCLUDE_UNRESOLVED",
                            "include 模块缺失、语法失败或存在多个候选。",
                            unit,
                            target,
                        )
                elif isinstance(value, ast.Tuple) and len(value.elts) == 2:
                    self.walk(unit, value.elts[0], prefix + part, chain, seen)
                elif (
                    isinstance(value, ast.Name)
                    and (import_name := self.index.name(unit, value))
                    and (other := self.index.module(import_name, unit))
                ):
                    self.walk(
                        other, ast.Name(id="urlpatterns"), prefix + part, chain, seen
                    )
                else:
                    self.walk(unit, value, prefix + part, chain, seen)
            else:
                self.view(unit, target, "/" + prefix + part, chain)
            return
        self.index.warn(
            "DYNAMIC_ROUTE", "路由集合、表达式或目标未能静态解析。", unit, expr
        )

    def view(
        self, unit: Unit, target: ast.AST, path: str, evidence: list[Evidence]
    ) -> None:
        if (
            isinstance(target, ast.Call)
            and isinstance(target.func, ast.Attribute)
            and target.func.attr == "as_view"
        ):
            resolved = self.index.resolve(unit, target.func.value)
            if not resolved or not isinstance(resolved[1], ast.ClassDef):
                self.index.warn(
                    "VIEW_UNRESOLVED",
                    "as_view 目标缺失、存在歧义或不是可识别类。",
                    unit,
                    target,
                )
                return
            info = self.rules.class_info(resolved[0], resolved[1])
            if (
                not info
                or not any(x.startswith("rest_framework.") for x in info.frameworks)
                or info.node.decorator_list
                or target.keywords
            ):
                self.index.warn(
                    "VIEW_UNRESOLVED",
                    "视图继承、类装饰器或 as_view 初始化参数未解析。",
                    unit,
                    target,
                )
                return
            if info.method("as_view") or info.method("dispatch"):
                self.index.warn(
                    "DYNAMIC_DISPATCH",
                    "自定义 as_view/dispatch 的运行时分派未解析。",
                    unit,
                    target,
                )
                return
            viewset = any("viewsets." in x for x in info.frameworks)
            actions = self.rules.actions(info, viewset)
            if viewset:
                if len(target.args) != 1 or not isinstance(target.args[0], ast.Dict):
                    self.index.warn(
                        "DYNAMIC_DISPATCH",
                        "ViewSet.as_view 需要字面量方法到动作映射。",
                        unit,
                        target,
                    )
                    return
                mapping: dict[str, str] = {}
                for key, value in zip(
                    target.args[0].keys, target.args[0].values, strict=True
                ):
                    method, action = literal_string(key), literal_string(value)
                    if (
                        method not in HTTP_METHODS
                        or action not in actions
                        or method in mapping
                    ):
                        self.index.warn(
                            "DYNAMIC_DISPATCH",
                            "方法映射包含未知或不唯一的动作。",
                            unit,
                            target,
                        )
                        return
                    mapping[method] = action
            elif target.args:
                self.index.warn(
                    "DYNAMIC_DISPATCH",
                    "APIView.as_view 的位置参数不受支持。",
                    unit,
                    target,
                )
                return
            else:
                mapping = {method: method for method in actions}
            self.emit_view(info, path, "django_path", mapping, evidence)
            return
        resolved = self.index.resolve(unit, target)
        if resolved and isinstance(
            resolved[1], (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            function_unit, function = resolved
            for decorator in function.decorator_list:
                if (
                    isinstance(decorator, ast.Call)
                    and self.index.name(function_unit, decorator.func)
                    == "rest_framework.decorators.api_view"
                ):
                    methods = (
                        decorator.args[0]
                        if decorator.args
                        else ast.List(elts=[ast.Constant(value="GET")])
                    )
                    if isinstance(methods, (ast.List, ast.Tuple)) and all(
                        (literal_string(x) or "").lower() in HTTP_METHODS
                        for x in methods.elts
                    ):
                        for method in sorted(
                            {str(literal_string(x)).upper() for x in methods.elts}
                            | {"OPTIONS"}
                        ):
                            self.add(
                                {
                                    "method": method,
                                    "path": path,
                                    "path_kind": "django_path",
                                    "action": function.name,
                                    "view": self.index.symbol(function_unit, function),
                                    "serializer": None,
                                    "model": None,
                                    "evidence": evidence
                                    + [
                                        self.evidence(
                                            function_unit, decorator, "drf.api_view"
                                        )
                                    ],
                                }
                            )
                        return
        self.index.warn(
            "VIEW_UNRESOLVED",
            "路由目标不是可识别的 DRF 视图或 api_view 函数。",
            unit,
            target,
        )

    def emit_view(
        self,
        info: ClassInfo,
        path: str,
        path_kind: str,
        mapping: dict[str, str],
        evidence: list[Evidence],
        serializer_override: tuple[Unit, ast.expr] | None = None,
    ) -> None:
        serializer, model, relation_evidence = self.rules.relations(
            info, serializer_override
        )
        actions = self.rules.actions(
            info, any("viewsets." in x for x in info.frameworks)
        )
        if "get" in mapping and "head" not in mapping:
            mapping = {**mapping, "head": mapping["get"]}
        mapping = {"options": "metadata", **mapping}
        allowed = info.attribute("http_method_names")
        if allowed:
            expr = allowed[1]
            if not isinstance(expr, (ast.List, ast.Tuple)) or not all(
                literal_string(x) in HTTP_METHODS for x in expr.elts
            ):
                self.index.warn(
                    "DYNAMIC_HTTP_METHODS",
                    "HTTP 方法限制不是受支持的静态列表。",
                    *allowed,
                )
                return
            mapping = {
                key: value
                for key, value in mapping.items()
                if key in {literal_string(x) for x in expr.elts}
            }
        for method, action in mapping.items():
            source = actions.get(action)
            action_evidence: Evidence = (
                self.evidence(*source, "python.method")
                if source
                else {
                    "kind": "framework_rule",
                    "rule": "drf/3.18.1." + action,
                    "source_ref": None,
                }
            )
            if method in {"head", "options"}:
                action_evidence = {
                    "kind": "framework_rule",
                    "rule": "drf/3.18.1." + method,
                    "source_ref": None,
                }
            self.add(
                {
                    "method": method.upper(),
                    "path": path,
                    "path_kind": "router_regex"
                    if path_kind == "router_regex"
                    else "django_path",
                    "action": action,
                    "view": self.index.symbol(info.unit, info.node),
                    "serializer": serializer,
                    "model": model,
                    "evidence": evidence + [action_evidence] + relation_evidence,
                }
            )

    def router(
        self,
        unit: Unit,
        name: str,
        prefix: str,
        evidence: list[Evidence],
        node: ast.AST,
    ) -> None:
        value = unit.values.get(name)
        if (
            name in unit.blocked
            or not isinstance(value, ast.Call)
            or self.index.name(unit, value.func)
            not in {
                "rest_framework.routers.SimpleRouter",
                "rest_framework.routers.DefaultRouter",
            }
        ):
            self.index.warn(
                "ROUTER_UNRESOLVED", "Router 不属于可确定的标准实例。", unit, node
            )
            return
        if value.args or any(
            k.arg not in {"trailing_slash", "use_regex_path"}
            or not isinstance(k.value, ast.Constant)
            or type(k.value.value) is not bool
            for k in value.keywords
        ):
            self.index.warn(
                "ROUTER_UNRESOLVED", "Router 配置不是受支持的布尔常量。", unit, value
            )
            return
        options = {
            k.arg: k.value.value
            for k in value.keywords
            if isinstance(k.value, ast.Constant)
        }
        trailing = "/" if options.get("trailing_slash", True) else ""
        regex = options.get("use_regex_path", True)
        default = (
            self.index.name(unit, value.func) == "rest_framework.routers.DefaultRouter"
        )
        prefix_regex = path_regex(prefix)
        if regex and prefix_regex is None:
            self.index.warn(
                "CUSTOM_CONVERTER",
                "自定义路径转换器无法转换为已知 Router 正则。",
                unit,
                node,
            )
            return
        registrations: list[ast.Call] = []
        for statement in unit.tree.body:
            if (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and dotted(statement.value.func) == name + ".register"
            ):
                if statement.lineno > getattr(node, "lineno", 10**9):
                    self.index.warn(
                        "ROUTER_ORDER_UNRESOLVED",
                        "路由集合求值后的注册不能确定是否生效。",
                        unit,
                        statement,
                    )
                    continue
                registrations.append(statement.value)
            elif isinstance(statement, (ast.Assign, ast.AugAssign)):
                targets = (
                    statement.targets
                    if isinstance(statement, ast.Assign)
                    else [statement.target]
                )
                if any((dotted(t) or "").startswith(name + ".") for t in targets):
                    self.index.warn(
                        "ROUTER_MUTATION",
                        "Router 属性存在修改，未推断其运行时路由。",
                        unit,
                        statement,
                    )
                    return
            elif isinstance(statement, (ast.If, ast.For, ast.While, ast.Try)):
                if any(
                    isinstance(x, ast.Call) and dotted(x.func) == name + ".register"
                    for x in ast.walk(statement)
                ):
                    self.index.warn(
                        "DYNAMIC_REGISTER",
                        "条件或循环中的 Router 注册未解析。",
                        unit,
                        statement,
                    )
        start = len(self.endpoints)
        basenames: set[str] = set()
        for call in registrations:
            if (
                len(call.args) not in {2, 3}
                or any(k.arg != "basename" for k in call.keywords)
                or (len(call.args) == 3 and call.keywords)
            ):
                self.index.warn(
                    "DYNAMIC_REGISTER",
                    "Router 注册参数不是受支持的静态形式。",
                    unit,
                    call,
                )
                continue
            part = literal_string(call.args[0])
            resolved = self.index.resolve(unit, call.args[1])
            if (
                part is None
                or not resolved
                or not isinstance(resolved[1], ast.ClassDef)
            ):
                self.index.warn(
                    "DYNAMIC_REGISTER", "Router 前缀或 ViewSet 引用未解析。", unit, call
                )
                continue
            info = self.rules.class_info(resolved[0], resolved[1])
            if (
                not info
                or not any("viewsets." in x for x in info.frameworks)
                or info.node.decorator_list
                or info.method("get_extra_actions")
                or info.method("as_view")
                or info.method("dispatch")
            ):
                self.index.warn(
                    "VIEW_UNRESOLVED",
                    "注册类的 ViewSet 继承或分派不受支持。",
                    unit,
                    call,
                )
                continue
            attrs = {
                key: info.attribute(key)
                for key in (
                    "lookup_field",
                    "lookup_url_kwarg",
                    "lookup_value_regex",
                    "lookup_value_converter",
                )
            }
            basename = (
                call.args[2]
                if len(call.args) == 3
                else next((k.value for k in call.keywords if k.arg == "basename"), None)
            )
            queryset = info.attribute("queryset")
            if basename is not None and literal_string(basename) is None:
                self.index.warn(
                    "DYNAMIC_BASENAME", "Router basename 不是静态字符串。", unit, call
                )
                continue
            if basename is None:
                queryset_model = None
                if (
                    queryset
                    and isinstance(queryset[1], ast.Call)
                    and isinstance(queryset[1].func, ast.Attribute)
                    and queryset[1].func.attr == "all"
                ):
                    manager = queryset[1].func.value
                    if isinstance(manager, ast.Attribute) and manager.attr == "objects":
                        queryset_model = self.index.resolve(queryset[0], manager.value)
                if (
                    not queryset_model
                    or not isinstance(queryset_model[1], ast.ClassDef)
                    or not (
                        model_info := self.rules.class_info(
                            queryset_model[0], queryset_model[1]
                        )
                    )
                    or "django.db.models.Model" not in model_info.frameworks
                ):
                    self.index.warn(
                        "BASENAME_UNRESOLVED",
                        "缺少 basename，且无法从静态 queryset 推导默认名称。",
                        unit,
                        call,
                    )
                    continue
                basename_value = queryset_model[1].name.lower()
            else:
                basename_value = literal_string(basename) or ""
            if basename_value in basenames:
                self.index.warn(
                    "DUPLICATE_BASENAME",
                    "Router basename 重复，框架注册将失败，未发布该 Router 的推断。",
                    unit,
                    call,
                )
                del self.endpoints[start:]
                return
            basenames.add(basename_value)
            if any(
                v is not None and literal_string(v[1]) is None for v in attrs.values()
            ):
                self.index.warn(
                    "DYNAMIC_LOOKUP", "动态 lookup 配置未解析。", unit, call
                )
                continue
            lookup = (
                literal_string(attrs["lookup_url_kwarg"][1])
                if attrs["lookup_url_kwarg"]
                else literal_string(attrs["lookup_field"][1])
                if attrs["lookup_field"]
                else "pk"
            )
            if not lookup or not lookup.isidentifier():
                self.index.warn(
                    "DYNAMIC_LOOKUP", "lookup 参数名称不受支持。", unit, call
                )
                continue
            if regex:
                pattern = (
                    literal_string(attrs["lookup_value_regex"][1])
                    if attrs["lookup_value_regex"]
                    else "[^/.]+"
                )
                detail = f"(?P<{lookup}>{pattern})"
            else:
                converter = (
                    literal_string(attrs["lookup_value_converter"][1])
                    if attrs["lookup_value_converter"]
                    else "str"
                )
                detail = f"<{converter}:{lookup}>"
            chain = evidence + [
                self.evidence(unit, call, "drf.router_register"),
                {
                    "kind": "framework_rule",
                    "rule": "drf/3.18.1.standard_router",
                    "source_ref": None,
                },
            ]
            actions = self.rules.actions(info, True)
            extras, valid_actions = router_actions(
                self.rules, info, set(ROUTER_ACTIONS)
            )
            if not valid_actions:
                del self.endpoints[start:]
                return
            for is_detail in (False, True):
                mapping = {
                    method.lower(): action
                    for action, (method, detail_flag) in ROUTER_ACTIONS.items()
                    if detail_flag == is_detail and action in actions
                }
                if mapping:
                    route = part + ("/" + detail if is_detail else "") + trailing
                    route = route.lstrip("/") if not part else route
                    full_path = (
                        "/"
                        + (
                            prefix_regex
                            if regex and prefix_regex is not None
                            else prefix
                        )
                        + route
                    )
                    self.emit_view(
                        info,
                        full_path + ("$" if regex else ""),
                        "router_regex" if regex else "django_path",
                        mapping,
                        chain,
                    )
            for extra in extras:
                if not extra.methods:
                    continue
                route = (
                    part
                    + ("/" + detail if extra.detail else "")
                    + "/"
                    + extra.path
                    + trailing
                )
                route = route.lstrip("/") if not part else route
                full_path = (
                    "/"
                    + (prefix_regex if regex and prefix_regex is not None else prefix)
                    + route
                )
                if len(full_path) > 2047:
                    self.index.warn("ROUTE_LIMIT", "动作路由完整路径超限。", unit, call)
                    continue
                self.emit_view(
                    info,
                    full_path + ("$" if regex else ""),
                    "router_regex" if regex else "django_path",
                    {method: extra.name for method in extra.methods},
                    chain + extra.evidence,
                    extra.serializer,
                )
        if default:
            for method in ("GET", "HEAD", "OPTIONS"):
                self.add(
                    {
                        "method": method,
                        "path": "/" + prefix,
                        "path_kind": "django_path",
                        "action": "api_root",
                        "view": None,
                        "serializer": None,
                        "model": None,
                        "evidence": evidence
                        + [
                            self.evidence(unit, value, "drf.default_router"),
                            {
                                "kind": "framework_rule",
                                "rule": "drf/3.18.1.api_root",
                                "source_ref": None,
                            },
                        ],
                    }
                )
            originals = list(self.endpoints[start:])
            for item in originals:
                # 格式后缀单独保留，不能删除后缀或斜杠后冒充相同 URL。
                path = item["path"].rstrip("$").rstrip("/")
                if item["path_kind"] == "django_path":
                    converted = path_regex(path)
                    if converted is None:
                        self.index.warn(
                            "CUSTOM_CONVERTER",
                            "格式后缀的自定义转换器未解析。",
                            unit,
                            node,
                        )
                        continue
                    path = converted
                suffix = r"\.(?P<format>[a-z0-9]+)/?$"
                if item["action"] == "api_root":
                    path = "/" + (prefix_regex or "")
                self.add(
                    {
                        **item,
                        "path": path + suffix,
                        "path_kind": "router_regex",
                        "evidence": item["evidence"]
                        + [
                            {
                                "kind": "framework_rule",
                                "rule": "drf/3.18.1.format_suffix",
                                "source_ref": None,
                            }
                        ],
                    }
                )


def analyze(
    snapshot_id: str, sources: list[Source], root_urlconf: str, skipped_files: int = 0
) -> AnalysisResult:
    index = PythonIndex(snapshot_id, sources)
    root = index.units.get(root_urlconf)
    if root is None or "urlpatterns" not in (root.values.keys() | root.imports.keys()):
        raise AnalysisFailed("root_urlconf_unavailable")
    parser = RouteParser(index)
    parser.walk(root, ast.Name(id="urlpatterns"), "", [])
    endpoints = sorted(
        parser.endpoints,
        key=lambda x: (x["path"], x["method"], x["view"]["name"] if x["view"] else ""),
    )
    seen: set[tuple[str, str, str]] = set()
    for endpoint in endpoints:
        key = (endpoint["method"], endpoint["path"], endpoint["path_kind"])
        if key in seen:
            index.warn(
                "DUPLICATE_ENDPOINT",
                "同方法及路径存在多个静态候选，未选定唯一处理器。",
                root,
                root.tree,
            )
        seen.add(key)
    return {
        "rule_version": RULE_VERSION,
        "coverage": {
            "python_files": len(index.units) + index.syntax_failed,
            "parsed_files": len(index.units),
            "syntax_failed_files": index.syntax_failed,
            "skipped_files": skipped_files,
            "endpoint_count": len(endpoints),
            "diagnostic_count": len(index.diagnostics),
            "complete": not index.diagnostics,
            "limitations": LIMITATIONS,
        },
        "endpoints": endpoints,
        "diagnostics": index.diagnostics,
    }
