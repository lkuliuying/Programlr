from typing import Any, cast

from apps.analysis.types import (
    MAX_RESULTS,
    RULE_VERSION,
    AnalysisFailed,
    AnalysisResult,
    Source,
)


def validate_result(
    value: Any, snapshot_id: str, sources: list[Source]
) -> AnalysisResult:
    lines = {s.file_path: max(1, len(s.content.splitlines())) for s in sources}
    return validate_stored_result(value, snapshot_id, lines, RULE_VERSION)


def validate_stored_result(
    value: Any, snapshot_id: str, lines: dict[str, int], rule_version: str
) -> AnalysisResult:
    """复用形状校验读取已保存版本；当前解析器仍固定校验自己的规则版本。"""

    def require(condition: bool) -> None:
        if not condition:
            raise AnalysisFailed("invalid_parser_result")

    def ref(item: Any) -> None:
        require(
            isinstance(item, dict)
            and set(item) == {"snapshot_id", "file_path", "start_line", "end_line"}
        )
        require(
            item["snapshot_id"] == snapshot_id
            and isinstance(item["file_path"], str)
            and item["file_path"] in lines
        )
        require(type(item["start_line"]) is int and type(item["end_line"]) is int)
        require(1 <= item["start_line"] <= item["end_line"] <= lines[item["file_path"]])

    require(
        isinstance(value, dict)
        and set(value) == {"rule_version", "coverage", "endpoints", "diagnostics"}
    )
    require(value["rule_version"] == rule_version)
    for key in ("endpoints", "diagnostics"):
        require(isinstance(value[key], list) and len(value[key]) <= MAX_RESULTS)
    for endpoint in value["endpoints"]:
        require(
            isinstance(endpoint, dict)
            and set(endpoint)
            == {
                "method",
                "path",
                "path_kind",
                "action",
                "view",
                "serializer",
                "model",
                "evidence",
            }
        )
        require(
            endpoint["method"]
            in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"}
        )
        require(endpoint["path_kind"] in {"django_path", "router_regex"})
        for key in ("path", "action"):
            require(
                isinstance(endpoint[key], str)
                and 0 < len(endpoint[key]) <= 8192
                and not any(ord(c) < 32 for c in endpoint[key])
            )
        for key in ("view", "serializer", "model"):
            symbol = endpoint[key]
            if symbol is not None:
                require(
                    isinstance(symbol, dict) and set(symbol) == {"name", "source_ref"}
                )
                require(
                    isinstance(symbol["name"], str) and symbol["name"].isidentifier()
                )
                ref(symbol["source_ref"])
        require(
            isinstance(endpoint["evidence"], list)
            and 0 < len(endpoint["evidence"]) <= 256
        )
        for evidence in endpoint["evidence"]:
            require(
                isinstance(evidence, dict)
                and set(evidence) == {"kind", "rule", "source_ref"}
            )
            require(
                evidence["kind"]
                in {"source_fact", "static_inference", "framework_rule"}
            )
            require(
                isinstance(evidence["rule"], str) and 0 < len(evidence["rule"]) <= 200
            )
            if evidence["source_ref"] is not None:
                ref(evidence["source_ref"])
            else:
                require(evidence["kind"] == "framework_rule")
    for diagnostic in value["diagnostics"]:
        require(
            isinstance(diagnostic, dict)
            and set(diagnostic) == {"code", "message", "severity", "source_ref"}
        )
        require(diagnostic["severity"] == "warning")
        require(
            isinstance(diagnostic["code"], str) and diagnostic["code"].isidentifier()
        )
        require(
            isinstance(diagnostic["message"], str)
            and 0 < len(diagnostic["message"]) <= 500
        )
        if diagnostic["source_ref"] is not None:
            ref(diagnostic["source_ref"])
    coverage = value["coverage"]
    counts = {
        "python_files",
        "parsed_files",
        "syntax_failed_files",
        "skipped_files",
        "endpoint_count",
        "diagnostic_count",
    }
    require(
        isinstance(coverage, dict)
        and set(coverage) == counts | {"complete", "limitations"}
    )
    require(all(type(coverage[key]) is int and coverage[key] >= 0 for key in counts))
    require(
        coverage["python_files"]
        == sum(path.endswith(".py") for path in lines)
        == coverage["parsed_files"] + coverage["syntax_failed_files"]
    )
    require(
        coverage["endpoint_count"] == len(value["endpoints"])
        and coverage["diagnostic_count"] == len(value["diagnostics"])
    )
    require(
        type(coverage["complete"]) is bool
        and coverage["complete"] == (not value["diagnostics"])
    )
    require(
        isinstance(coverage["limitations"], list)
        and 0 < len(coverage["limitations"]) <= 20
        and all(isinstance(x, str) and len(x) <= 500 for x in coverage["limitations"])
    )
    return cast(AnalysisResult, value)
