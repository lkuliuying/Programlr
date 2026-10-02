"""校验计算结果与持久化读取的形状、双侧归属和预算。"""

import json
import re
import uuid
from pathlib import PurePosixPath
from typing import Any, cast

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

from apps.analysis.diffs.types import (
    COMPARISON_VERSION,
    FILE_CHANGE_TYPES,
    MAX_FILE_DIFF_BYTES,
    MAX_FILES,
    MAX_OUTPUT_BYTES,
    SEMANTIC_CHANGE_TYPES,
    ComparisonData,
    ComparisonFailed,
)
from apps.analysis.types import GraphData


def obj(**properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "required": list(properties),
        "additionalProperties": False,
        "properties": properties,
    }


def array(items: dict[str, Any], maximum: int = 30_000) -> dict[str, Any]:
    return {"type": "array", "items": items, "maxItems": maximum}


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


TEXT = {"type": "string", "maxLength": 8192}
ID = {
    "type": "string",
    "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
}
NUMBER = {"type": "integer", "minimum": 0, "maximum": 2147483647}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
REF = obj(
    snapshot_id=ID,
    file_path={"type": "string", "maxLength": 1024},
    start_line={"type": "integer", "minimum": 1},
    end_line={"type": "integer", "minimum": 1},
)
PROOF = obj(
    kind={"enum": ["source_fact", "static_inference", "framework_rule"]},
    rule=TEXT,
    source_ref=nullable(REF),
)
VERSION = obj(
    analysis_id=ID,
    snapshot_id=ID,
    root_urlconf=TEXT,
    rule_version=TEXT,
    graph_version=nullable(TEXT),
    frontend_rule_version=nullable(TEXT),
    association_rule_version=nullable(TEXT),
)
FILE = obj(
    id=ID,
    file_path={"type": "string", "maxLength": 1024},
    change_type={"enum": FILE_CHANGE_TYPES},
    base_ref=nullable(REF),
    target_ref=nullable(REF),
    base_sha256=nullable(HASH),
    target_sha256=nullable(HASH),
    diff={"type": "string", "maxLength": MAX_FILE_DIFF_BYTES},
    base_ranges=array(REF),
    target_ranges=array(REF),
)
INTERFACE = obj(
    method={
        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
    },
    path=TEXT,
    path_kind={"enum": ["django_path", "router_regex"]},
    change_type={"enum": SEMANTIC_CHANGE_TYPES},
    base_indices=array(NUMBER, 10_000),
    target_indices=array(NUMBER, 10_000),
    changed_fields=array(
        {"enum": ["action", "view", "serializer", "model", "relations"]}, 5
    ),
    base_evidence=array(PROOF),
    target_evidence=array(PROOF),
)
RELATION = obj(
    relation={
        "enum": [
            "route_view",
            "serializer_class",
            "meta_model",
            "direct_call",
            "contains_function",
            "contains_request",
            "callback_binding",
            "method_path_match",
            "candidate_match",
        ]
    },
    source_name=TEXT,
    target_name=TEXT,
    change_type={"enum": SEMANTIC_CHANGE_TYPES},
    base_edge_ids=array(ID),
    target_edge_ids=array(ID),
    base_evidence=array(PROOF),
    target_evidence=array(PROOF),
)
APPLICABILITY = obj(
    source_ref=REF,
    target_ref=nullable(REF),
    applicability={"enum": ["unchanged", "review", "deleted", "unknown"]},
)
EVIDENCE = obj(
    explanation_id=ID,
    preview_id=ID,
    analysis_id=ID,
    endpoint_index=NUMBER,
    references=array(APPLICABILITY, 480),
    warning=nullable(TEXT),
)
SCHEMA = obj(
    comparison_version={"const": COMPARISON_VERSION},
    summary=obj(**{name: NUMBER for name in FILE_CHANGE_TYPES}),
    files=array(FILE, MAX_FILES),
    comparability={"enum": ["comparable", "files_only", "incomparable"]},
    comparison_notes=array(TEXT, 20),
    base_version=nullable(VERSION),
    target_version=nullable(VERSION),
    interfaces=array(INTERFACE, 20_000),
    relations=array(RELATION, 60_000),
    evidence=array(EVIDENCE, 200),
)


def validate_comparison(
    value: Any,
    comparison_id: str,
    base_id: str,
    target_id: str,
    analysis_ids: tuple[str | None, str | None],
    graphs: tuple[GraphData | None, GraphData | None],
) -> ComparisonData:
    def require(condition: bool) -> None:
        if not condition:
            raise ComparisonFailed("invalid_comparison_result")

    try:
        require(len(json.dumps(value, ensure_ascii=True).encode()) <= MAX_OUTPUT_BYTES)
        Draft202012Validator(SCHEMA).validate(value)
        # Schema 已校验完整 JSON 形状；动态字段名仅用于逐侧归属检查。
        data: dict[str, Any] = value
        paths: dict[str, dict[str, Any]] = {"base": {}, "target": {}}
        summary = {name: 0 for name in FILE_CHANGE_TYPES}
        require(
            len({file["file_path"] for file in data["files"]}) == len(data["files"])
        )
        require(
            [file["file_path"] for file in data["files"]]
            == sorted(file["file_path"] for file in data["files"])
        )
        for file in data["files"]:
            path = file["file_path"]
            require(
                bool(path)
                and all(part not in {"", ".", ".."} for part in path.split("/"))
                and PurePosixPath(path).as_posix() == path
                and not PurePosixPath(path).is_absolute()
                and ".." not in PurePosixPath(path).parts
                and not re.search(r"[\\:\x00-\x1f]", path)
            )
            require(file["id"] == str(uuid.uuid5(uuid.UUID(comparison_id), path)))
            summary[file["change_type"]] += 1
            for side, snapshot in (("base", base_id), ("target", target_id)):
                ref, digest = file[side + "_ref"], file[side + "_sha256"]
                require((ref is None) == (digest is None))
                if ref:
                    require(
                        ref["snapshot_id"] == snapshot
                        and ref["file_path"] == path
                        and ref["start_line"] == 1
                    )
                    paths[side][path] = ref
            before, after = file["base_ref"], file["target_ref"]
            require(before is not None or after is not None)
            expected = (
                "added"
                if before is None
                else "deleted"
                if after is None
                else "unchanged"
                if file["base_sha256"] == file["target_sha256"]
                else "modified"
            )
            require(file["change_type"] == expected)
            require(len(file["diff"].encode()) <= MAX_FILE_DIFF_BYTES)
            if expected == "unchanged":
                require(
                    not file["diff"]
                    and not file["base_ranges"]
                    and not file["target_ranges"]
                )
        require(data["summary"] == summary)
        if data["comparability"] == "comparable":
            before_version, after_version = data["base_version"], data["target_version"]
            require(before_version is not None and after_version is not None)
            require(
                all(
                    before_version[field] == after_version[field]
                    for field in (
                        "root_urlconf",
                        "rule_version",
                        "graph_version",
                        "frontend_rule_version",
                        "association_rule_version",
                    )
                )
            )
        elif data["comparability"] == "files_only":
            require(data["base_version"] is None and data["target_version"] is None)

        def reference(ref: Any, side: str, snapshot: str) -> None:
            known = paths[side].get(ref["file_path"])
            require(
                known is not None
                and ref["snapshot_id"] == snapshot
                and 1 <= ref["start_line"] <= ref["end_line"] <= known["end_line"]
            )

        for side, snapshot, analysis_id, graph in zip(
            ("base", "target"), (base_id, target_id), analysis_ids, graphs, strict=True
        ):
            version = data[side + "_version"]
            require((version is None) == (analysis_id is None))
            if version:
                require(
                    version["analysis_id"] == analysis_id
                    and version["snapshot_id"] == snapshot
                )
            for file in data["files"]:
                for ref in file[side + "_ranges"]:
                    require(ref["file_path"] == file["file_path"])
                    reference(ref, side, snapshot)
            if data["comparability"] == "comparable":
                require(graph is not None)
                assert graph is not None
                ids = {edge["id"] for edge in graph["edges"]}
                endpoints = {
                    node["endpoint"]["index"]: node["endpoint"]
                    for node in graph["nodes"]
                    if node["endpoint"]
                }
                for item in data["interfaces"]:
                    for index in item[side + "_indices"]:
                        require(
                            index in endpoints
                            and (
                                endpoints[index]["method"],
                                endpoints[index]["path"],
                                endpoints[index]["path_kind"],
                            )
                            == (item["method"], item["path"], item["path_kind"])
                        )
                for relation in data["relations"]:
                    require(set(relation[side + "_edge_ids"]) <= ids)
            for item in [*data["interfaces"], *data["relations"]]:
                for proof in item[side + "_evidence"]:
                    if proof["source_ref"]:
                        reference(proof["source_ref"], side, snapshot)
                    else:
                        require(proof["kind"] == "framework_rule")
        if data["comparability"] != "comparable":
            require(not data["interfaces"] and not data["relations"])
        for entry in data["evidence"]:
            for item in entry["references"]:
                # 无法核验的历史引用只返回安全的已有位置，不能带入任意路径。
                reference(item["source_ref"], "base", base_id)
                if item["target_ref"]:
                    require(item["applicability"] == "unchanged")
                    reference(item["target_ref"], "target", target_id)
        return cast(ComparisonData, data)
    except (
        ValidationError,
        KeyError,
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
    ):
        raise ComparisonFailed("invalid_comparison_result") from None
