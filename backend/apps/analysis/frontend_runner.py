"""调用固定 Node 解析器并验证不可信的跨进程输出。"""

import json
import os
import subprocess
import threading
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryFile
from typing import Any, cast

# 锁定的 jsonschema 未提供内置声明；仅在此运行时校验边界接受该包的未注解导入。
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

from apps.analysis.frontend_types import (
    FRONTEND_RULE_VERSION,
    PROTOCOL_VERSION,
    FrontendResult,
)
from apps.analysis.types import (
    MAX_OUTPUT_BYTES,
    PARSER_TIMEOUT_SECONDS,
    AnalysisFailed,
    Source,
)

ROOT = Path(__file__).resolve().parents[3]
PARSER_PATH = ROOT / "analyzers/typescript/dist/cli.js"
NODE_PATH = (
    ROOT / ".runtime/tools/node-v24.21.0-win-x64/node.exe"
    if os.name == "nt"
    else Path("/usr/local/bin/node")
)


@lru_cache(maxsize=3)
def protocol_validator(section: str) -> Draft202012Validator:
    schema = json.loads(
        (ROOT / "contracts/typescript-analysis.schema.json").read_text(encoding="utf-8")
    )
    return Draft202012Validator({**schema, "oneOf": [{"$ref": f"#/$defs/{section}"}]})


def validate_frontend(
    value: Any, snapshot_id: str, line_counts: dict[str, int]
) -> FrontendResult:
    def require(condition: bool) -> None:
        if not condition:
            raise AnalysisFailed("invalid_frontend_result")

    try:
        protocol_validator("output").validate(value)
    except (ValidationError, ValueError, TypeError, RecursionError):
        raise AnalysisFailed("invalid_frontend_result") from None
    require(value["snapshot_id"] == snapshot_id)
    ids = {item["id"] for item in value["functions"] + value["requests"]}
    functions = {item["id"] for item in value["functions"]}
    requests = {item["id"]: item for item in value["requests"]}
    require(len(ids) == len(value["functions"]) + len(value["requests"]))

    def check_ref(item: Any) -> None:
        require(item["snapshot_id"] == snapshot_id and item["file_path"] in line_counts)
        require(
            1
            <= item["start_line"]
            <= item["end_line"]
            <= line_counts[item["file_path"]]
        )

    for item in value["functions"] + value["requests"]:
        check_ref(item["source_ref"])
        for evidence in item.get("evidence", []) + item.get("entry_points", []):
            check_ref(evidence["source_ref"])
    for request in value["requests"]:
        require(request["owner_id"] is None or request["owner_id"] in functions)
        if request["resolution"] == "static":
            require(
                request["method"] is not None
                and isinstance(request["path"], str)
                and request["path"].startswith("/")
            )
    contained: set[str] = set()
    for relation in value["relations"]:
        require(relation["source_id"] in functions and relation["target_id"] in ids)
        if relation["relation"] == "contains_request":
            require(relation["target_id"] in requests)
            require(
                requests[relation["target_id"]]["owner_id"] == relation["source_id"]
            )
            require(relation["target_id"] not in contained)
            contained.add(relation["target_id"])
        else:
            require(relation["target_id"] in functions)
        for evidence in relation["evidence"]:
            check_ref(evidence["source_ref"])
    require(
        contained
        == {item["id"] for item in value["requests"] if item["owner_id"] is not None}
    )
    for item in value["diagnostics"]:
        if item["source_ref"] is not None:
            check_ref(item["source_ref"])
    coverage = value["coverage"]
    require(coverage["source_files"] == len(line_counts))
    require(
        coverage["parsed_files"] + coverage["syntax_failed_files"] == len(line_counts)
    )
    require(coverage["function_count"] == len(value["functions"]))
    require(coverage["request_count"] == len(value["requests"]))
    require(coverage["complete"] == (not value["diagnostics"]))
    return cast(FrontendResult, value)


def run_frontend_parser(snapshot_id: str, sources: list[Source]) -> FrontendResult:
    if not sources:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "rule_version": FRONTEND_RULE_VERSION,
            "snapshot_id": snapshot_id,
            "functions": [],
            "requests": [],
            "relations": [],
            "diagnostics": [],
            "coverage": {
                "source_files": 0,
                "parsed_files": 0,
                "syntax_failed_files": 0,
                "function_count": 0,
                "request_count": 0,
                "complete": True,
                "limitations": ["当前快照没有前端源文件；静态关联不代表运行轨迹。"],
            },
        }
    payload = json.dumps(
        {
            "protocol_version": PROTOCOL_VERSION,
            "snapshot_id": snapshot_id,
            "sources": [asdict(source) for source in sources],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    if len(payload) > 128 * 1024 * 1024:
        raise AnalysisFailed("frontend_input_limit")
    output = bytearray()
    exceeded = threading.Event()
    environment = {"PATH": str(NODE_PATH.parent), "LANG": "C.UTF-8"}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    try:
        with TemporaryFile() as incoming:
            incoming.write(payload)
            incoming.seek(0)
            with subprocess.Popen(
                [str(NODE_PATH), "--max-old-space-size=256", str(PARSER_PATH)],
                stdin=incoming,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=PARSER_PATH.parent,
                env=environment,
            ) as process:
                assert process.stdout is not None
                stream = process.stdout

                def collect() -> None:
                    while chunk := stream.read(65536):
                        if len(output) + len(chunk) > MAX_OUTPUT_BYTES:
                            exceeded.set()
                            process.kill()
                            return
                        output.extend(chunk)

                reader = threading.Thread(target=collect)
                reader.start()
                try:
                    process.wait(timeout=PARSER_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise AnalysisFailed("frontend_parser_timeout") from None
                finally:
                    reader.join()
                if exceeded.is_set():
                    raise AnalysisFailed("frontend_output_limit")
                if process.returncode not in {0, 2}:
                    raise AnalysisFailed("frontend_parser_process_failed")
                decoded = json.loads(output)
                if process.returncode == 2:
                    protocol_validator("failure").validate(decoded)
                    raise AnalysisFailed("frontend_" + decoded["failure"])
        if (
            not isinstance(decoded, dict)
            or decoded.get("rule_version") != FRONTEND_RULE_VERSION
        ):
            raise AnalysisFailed("frontend_parser_rule_version")
        return validate_frontend(
            decoded,
            snapshot_id,
            {
                source.file_path: max(
                    1, source.content.count("\n") + (not source.content.endswith("\n"))
                )
                for source in sources
            },
        )
    except (OSError, ValueError, TypeError, ValidationError, RecursionError):
        raise AnalysisFailed("frontend_parser_protocol_or_io_failed") from None
