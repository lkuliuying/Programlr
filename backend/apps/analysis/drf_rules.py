import ast
from dataclasses import dataclass

from apps.analysis.python_index import Definition, PythonIndex, Unit, assignment
from apps.analysis.types import Evidence, Symbol

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
VIEW_ACTIONS = {
    "rest_framework.viewsets.ModelViewSet": {
        "list",
        "create",
        "retrieve",
        "update",
        "partial_update",
        "destroy",
    },
    "rest_framework.viewsets.ReadOnlyModelViewSet": {"list", "retrieve"},
    "rest_framework.mixins.ListModelMixin": {"list"},
    "rest_framework.mixins.CreateModelMixin": {"create"},
    "rest_framework.mixins.RetrieveModelMixin": {"retrieve"},
    "rest_framework.mixins.UpdateModelMixin": {"update", "partial_update"},
    "rest_framework.mixins.DestroyModelMixin": {"destroy"},
}
GENERIC_METHODS = {
    "CreateAPIView": {"post"},
    "ListAPIView": {"get"},
    "RetrieveAPIView": {"get"},
    "DestroyAPIView": {"delete"},
    "UpdateAPIView": {"put", "patch"},
    "ListCreateAPIView": {"get", "post"},
    "RetrieveUpdateAPIView": {"get", "put", "patch"},
    "RetrieveDestroyAPIView": {"get", "delete"},
    "RetrieveUpdateDestroyAPIView": {"get", "put", "patch", "delete"},
}
KNOWN_BASES = {
    "rest_framework.views.APIView",
    "rest_framework.generics.GenericAPIView",
    "rest_framework.viewsets.ViewSet",
    "rest_framework.viewsets.GenericViewSet",
    "rest_framework.serializers.Serializer",
    "rest_framework.serializers.ModelSerializer",
    "rest_framework.serializers.HyperlinkedModelSerializer",
    "django.db.models.Model",
    *VIEW_ACTIONS,
    *(f"rest_framework.generics.{name}" for name in GENERIC_METHODS),
}


@dataclass
class ClassInfo:
    unit: Unit
    node: ast.ClassDef
    lineage: list[tuple[Unit, ast.ClassDef]]
    frameworks: set[str]

    def method(self, name: str) -> tuple[Unit, Definition] | None:
        for unit, node in self.lineage:
            for child in node.body:
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == name
                ):
                    return unit, child
                if isinstance(child, (ast.If, ast.Try, ast.For, ast.While)):
                    for item in ast.walk(child):
                        if (
                            isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and item.name == name
                        ):
                            return unit, item
        return None

    def attribute(self, name: str) -> tuple[Unit, ast.expr] | None:
        for unit, node in self.lineage:
            for child in node.body:
                if isinstance(child, (ast.If, ast.Try, ast.For, ast.While, ast.With)):
                    if any(
                        isinstance(item, ast.Name)
                        and isinstance(item.ctx, ast.Store)
                        and item.id == name
                        for item in ast.walk(child)
                    ):
                        return unit, ast.Constant(value=None)
            matches = [
                (unit, pair[1])
                for child in node.body
                if (pair := assignment(child)) and pair[0] == name
            ]
            if len(matches) == 1:
                return matches[0]
            if matches:
                return unit, ast.Constant(value=None)
        return None


class DrfRules:
    def __init__(self, index: PythonIndex) -> None:
        self.index = index

    def class_info(
        self,
        unit: Unit,
        node: ast.ClassDef,
        seen: frozenset[tuple[str, str]] = frozenset(),
    ) -> ClassInfo | None:
        if (unit.path, node.name) in seen or len(seen) >= 32:
            return None
        lineage = [(unit, node)]
        frameworks: set[str] = set()
        local_bases = 0
        for base in node.bases:
            name = self.index.name(unit, base)
            if name in KNOWN_BASES:
                frameworks.add(name)
                continue
            resolved = self.index.resolve(unit, base)
            if resolved is None or not isinstance(resolved[1], ast.ClassDef):
                return None
            parent = self.class_info(
                resolved[0], resolved[1], seen | {(unit.path, node.name)}
            )
            if parent is None:
                return None
            local_bases += 1
            lineage.extend(parent.lineage)
            frameworks.update(parent.frameworks)
        # 多个用户基类的 C3 分派不在当前规则内，不能靠 DFS 顺序冒充实际 MRO。
        if local_bases > 1 or node.keywords:
            return None
        return ClassInfo(unit, node, lineage, frameworks)

    def actions(
        self, info: ClassInfo, viewset: bool
    ) -> dict[str, tuple[Unit, Definition] | None]:
        actions: dict[str, tuple[Unit, Definition] | None] = {}
        for base in info.frameworks:
            names = (
                VIEW_ACTIONS.get(base, set())
                if viewset
                else GENERIC_METHODS.get(base.rsplit(".", 1)[-1], set())
            )
            for name in names:
                actions[name] = None
        for unit, node in reversed(info.lineage):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if viewset or child.name in HTTP_METHODS:
                        actions[child.name] = (unit, child)
                elif (pair := assignment(child)) and (
                    pair[0] in actions or pair[0] in HTTP_METHODS
                ):
                    actions.pop(pair[0], None)
                    self.index.warn(
                        "DYNAMIC_ACTION",
                        "方法被属性赋值覆盖，未推断可调用动作。",
                        unit,
                        child,
                    )
                elif isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                    for item in ast.walk(child):
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            actions.pop(item.name, None)
                            self.index.warn(
                                "DYNAMIC_ACTION", "条件方法定义未解析。", unit, item
                            )
        return actions

    def relations(
        self, info: ClassInfo, serializer_override: tuple[Unit, ast.expr] | None = None
    ) -> tuple[Symbol | None, Symbol | None, list[Evidence]]:
        evidence: list[Evidence] = []
        dynamic = info.method("get_serializer_class") or info.method("get_serializer")
        if dynamic:
            self.index.warn(
                "DYNAMIC_SERIALIZER",
                "自定义序列化器选择或构造方法的运行时行为未解析。",
                *dynamic,
            )
            return None, None, evidence
        attribute = serializer_override or info.attribute("serializer_class")
        if not attribute:
            self.index.warn(
                "SERIALIZER_UNRESOLVED",
                "未找到可静态确定的 serializer_class。",
                info.unit,
                info.node,
            )
            return None, None, evidence
        resolved = self.index.resolve(*attribute)
        if not resolved or not isinstance(resolved[1], ast.ClassDef):
            self.index.warn(
                "SERIALIZER_UNRESOLVED",
                "序列化器引用不存在、存在歧义或为动态表达式。",
                *attribute,
            )
            return None, None, evidence
        serializer_info = self.class_info(resolved[0], resolved[1])
        serializer_bases = {
            "rest_framework.serializers.Serializer",
            "rest_framework.serializers.ModelSerializer",
            "rest_framework.serializers.HyperlinkedModelSerializer",
        }
        if serializer_info is None or not (
            serializer_info.frameworks & serializer_bases
        ):
            self.index.warn(
                "SERIALIZER_UNRESOLVED", "序列化器继承关系超出静态支持范围。", *resolved
            )
            return None, None, evidence
        serializer = self.index.symbol(*resolved)
        evidence.append(
            {
                "kind": "static_inference",
                "rule": "drf.action_serializer_class"
                if serializer_override
                else "drf.serializer_class",
                "source_ref": self.index.ref(*attribute),
            }
        )
        if not (
            serializer_info.frameworks
            & {
                "rest_framework.serializers.ModelSerializer",
                "rest_framework.serializers.HyperlinkedModelSerializer",
            }
        ):
            return serializer, None, evidence
        for unit, cls in serializer_info.lineage:
            meta = next(
                (
                    x
                    for x in cls.body
                    if isinstance(x, ast.ClassDef) and x.name == "Meta"
                ),
                None,
            )
            if meta:
                if any(
                    isinstance(item, (ast.If, ast.Try, ast.For, ast.While))
                    for item in meta.body
                ):
                    break
                values = [
                    pair[1]
                    for child in meta.body
                    if (pair := assignment(child)) and pair[0] == "model"
                ]
                model = (
                    self.index.resolve(unit, values[0])
                    if len(values) == 1 and not meta.bases
                    else None
                )
                if model and isinstance(model[1], ast.ClassDef):
                    model_info = self.class_info(model[0], model[1])
                    if model_info and "django.db.models.Model" in model_info.frameworks:
                        evidence.append(
                            {
                                "kind": "static_inference",
                                "rule": "drf.model_serializer_meta_model",
                                "source_ref": self.index.ref(unit, values[0]),
                            }
                        )
                        return serializer, self.index.symbol(*model), evidence
                break
        self.index.warn(
            "MODEL_UNRESOLVED",
            "ModelSerializer.Meta.model 未能唯一解析到源码模型。",
            *resolved,
        )
        return serializer, None, evidence
