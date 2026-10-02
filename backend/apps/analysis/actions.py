"""识别标准 Router 的明确装饰动作，不执行源码或恢复动态方法映射。"""

import ast
from dataclasses import dataclass

from apps.analysis.drf_rules import HTTP_METHODS, ClassInfo, DrfRules
from apps.analysis.python_index import Unit, dotted, literal_string
from apps.analysis.types import Evidence


@dataclass(frozen=True)
class RouterAction:
    name: str
    detail: bool
    methods: tuple[str, ...]
    path: str
    evidence: list[Evidence]
    serializer: tuple[Unit, ast.expr] | None


def router_actions(
    rules: DrfRules, info: ClassInfo, reserved: set[str]
) -> tuple[list[RouterAction], bool]:
    index = rules.index
    actions: list[RouterAction] = []
    mapped: set[str] = set()
    for unit, cls in info.lineage:
        for node in cls.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    expression = (
                        decorator.func if isinstance(decorator, ast.Call) else decorator
                    )
                    name = dotted(expression)
                    if name and ".mapping." in name:
                        mapped.add(name.split(".")[0])
                        index.warn(
                            "CUSTOM_ACTION_UNRESOLVED",
                            "动作的二次方法映射未解析。",
                            unit,
                            decorator,
                        )
    for name, source in sorted(rules.actions(info, True).items()):
        if source is None:
            continue
        unit, node = source
        if (
            not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or not node.decorator_list
        ):
            continue
        decorator = node.decorator_list[0]
        recognized = (
            isinstance(decorator, ast.Call)
            and index.name(unit, decorator.func) == "rest_framework.decorators.action"
        )
        # 类作用域可以遮蔽模块导入，不能仅凭模块索引判定装饰器身份。
        root = (
            (dotted(decorator.func) or "").split(".")[0]
            if isinstance(decorator, ast.Call)
            else ""
        )
        cls = next(
            cls for owner, cls in info.lineage if owner is unit and node in cls.body
        )
        if any(
            item.lineno < decorator.lineno
            and (
                item.name == root
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                )
                else any(
                    isinstance(child, ast.Name)
                    and isinstance(child.ctx, (ast.Store, ast.Del))
                    and child.id == root
                    for child in ast.walk(item)
                )
            )
            for item in cls.body
        ):
            recognized = False
        if recognized and name in reserved:
            index.warn(
                "INVALID_ACTION",
                "action 与标准动作重名，标准 Router 将拒绝注册。",
                unit,
                node,
            )
            return [], False
        if not recognized or len(node.decorator_list) != 1 or name in mapped:
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "动作装饰器、绑定或额外装饰超出明确支持范围。",
                unit,
                node,
            )
            continue
        assert isinstance(decorator, ast.Call)
        values = {keyword.arg: keyword.value for keyword in decorator.keywords}
        if (
            decorator.args
            or len(values) != len(decorator.keywords)
            or set(values)
            - {"detail", "methods", "url_path", "url_name", "serializer_class"}
            or not isinstance(values.get("detail"), ast.Constant)
            or type(getattr(values.get("detail"), "value", None)) is not bool
        ):
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "action 需要明确 detail 布尔值及受支持的字面量参数。",
                unit,
                decorator,
            )
            continue
        methods = values.get("methods", ast.List(elts=[ast.Constant(value="get")]))
        if isinstance(methods, ast.Constant) and methods.value is None:
            methods = ast.List(elts=[ast.Constant(value="get")])
        if not isinstance(methods, (ast.List, ast.Tuple)) or any(
            (literal_string(item) or "").lower() not in HTTP_METHODS
            for item in methods.elts
        ):
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "action methods 不是受支持的方法字面量列表。",
                unit,
                decorator,
            )
            continue
        url = values.get("url_path", ast.Constant(value=None))
        path = (
            name
            if isinstance(url, ast.Constant) and url.value is None
            else literal_string(url)
        )
        if path is None or len(path) > 1024 or any(ord(char) < 32 for char in path):
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "action url_path 不是有界字面量字符串。",
                unit,
                decorator,
            )
            continue
        if "url_name" in values and not (
            literal_string(values["url_name"]) is not None
            or isinstance(values["url_name"], ast.Constant)
            and values["url_name"].value is None
        ):
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "动态 action url_name 未解析。",
                unit,
                decorator,
            )
            continue
        serializer = values.get("serializer_class")
        if serializer is not None and not isinstance(
            serializer, (ast.Name, ast.Attribute)
        ):
            index.warn(
                "CUSTOM_ACTION_UNRESOLVED",
                "action 序列化器不是直接指定的引用。",
                unit,
                decorator,
            )
            continue
        detail_node = values["detail"]
        assert isinstance(detail_node, ast.Constant)
        assert isinstance(detail_node.value, bool)
        actions.append(
            RouterAction(
                name=name,
                detail=detail_node.value,
                methods=tuple(
                    dict.fromkeys(
                        (literal_string(item) or "").lower() for item in methods.elts
                    )
                ),
                path=path or name,
                serializer=(unit, serializer) if serializer is not None else None,
                evidence=[
                    {
                        "kind": "source_fact",
                        "rule": "drf.action",
                        "source_ref": index.ref(unit, decorator),
                    },
                    {
                        "kind": "framework_rule",
                        "rule": "drf/3.18.1.action_defaults",
                        "source_ref": None,
                    },
                ],
            )
        )
    return actions, True
