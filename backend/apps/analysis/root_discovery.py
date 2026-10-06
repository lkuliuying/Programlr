"""仅用有界 AST 发现 URLconf；配置有分歧时保留选择，不执行设置。"""

import ast
from typing import Any

from apps.analysis.python_index import PythonIndex, Unit, literal_string
from apps.analysis.types import Source

SCAN_VERSION = "source-scan/1.0.0"


def discover_roots(snapshot_id: str, sources: list[Source]) -> dict[str, Any]:
    index = PythonIndex(snapshot_id, sources)
    candidates: dict[str, dict[str, Any]] = {}
    configured: set[str] = set()
    config_invalid = False
    for unit in index.units.values():
        if (
            "urlpatterns" in (unit.values.keys() | unit.imports.keys())
            and "urlpatterns" not in unit.blocked
        ):
            candidates[unit.path] = {
                "file_path": unit.path,
                "module": unit.path.removesuffix(".py").replace("/", "."),
                "reason": "static_urlpatterns",
                "source_refs": [
                    index.ref(unit, unit.values.get("urlpatterns", unit.tree))
                ],
            }
    for unit in index.units.values():
        if "ROOT_URLCONF" not in unit.values:
            continue
        value = literal_string(unit.values["ROOT_URLCONF"])
        if value is None or "ROOT_URLCONF" in unit.blocked:
            index.warn(
                "ROOT_CONFIGURATION_DYNAMIC",
                "ROOT_URLCONF 不能静态确定，请核对候选根。",
                unit,
                unit.values["ROOT_URLCONF"],
            )
            config_invalid = True
            continue
        configured.add(value)
        target = index.module(value, unit)
        if target is None or target.path not in candidates:
            index.warn(
                "ROOT_CONFIGURATION_UNAVAILABLE",
                "配置的根路由未能唯一定位到可用 urlpatterns。",
                unit,
                unit.values["ROOT_URLCONF"],
            )
            config_invalid = True
            continue
        candidates[target.path]["reason"] = "literal_root_urlconf"
        candidates[target.path]["source_refs"].append(
            index.ref(unit, unit.values["ROOT_URLCONF"])
        )
    included: set[str] = set()
    for unit in index.units.values():
        if unit.path not in candidates:
            continue
        for node in ast.walk(unit.values.get("urlpatterns", unit.tree)):
            if (
                not isinstance(node, ast.Call)
                or index.name(unit, node.func) != "django.urls.include"
                or not node.args
            ):
                continue
            value = literal_string(node.args[0])
            included_unit: Unit | None = index.module(value, unit) if value else None
            if (
                included_unit
                and included_unit.path in candidates
                and included_unit.path != unit.path
            ):
                included.add(included_unit.path)
    choices = [
        item
        for path, item in candidates.items()
        if item["reason"] == "literal_root_urlconf"
    ]
    selected: str | None = None
    if len(configured) == 1 and len(choices) == 1 and not config_invalid:
        selected = choices[0]["file_path"]
    elif not configured and not config_invalid:
        top = [item for path, item in candidates.items() if path not in included]
        if len(top) == 1:
            selected = top[0]["file_path"]
        elif top:
            choices = top
    if not choices:
        choices = list(candidates.values())
    if len(choices) > 2000:
        choices = choices[:2000]
        selected = None
    return {
        "scan_version": SCAN_VERSION,
        "status": "selected" if selected else "needs_root" if choices else "no_root",
        "selected_root": selected,
        "candidates": sorted(choices, key=lambda item: item["file_path"]),
        "diagnostics": index.diagnostics,
    }
