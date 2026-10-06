"""扫描使用既有受控解析进程，输出只允许快照内引用。"""

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryFile
from typing import Any

from apps.analysis.root_discovery import SCAN_VERSION
from apps.analysis.types import (
    MAX_OUTPUT_BYTES,
    PARSER_TIMEOUT_SECONDS,
    AnalysisFailed,
    Source,
)


def validate_scan(
    value: Any, snapshot_id: str, sources: list[Source]
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"roots", "knowledge"}:
        raise AnalysisFailed("invalid_scan_result")
    roots = value["roots"]
    if (
        not isinstance(roots, dict)
        or set(roots)
        != {"scan_version", "status", "selected_root", "candidates", "diagnostics"}
        or roots.get("scan_version") != SCAN_VERSION
        or roots.get("status") not in {"selected", "needs_root", "no_root"}
        or not isinstance(roots.get("candidates"), list)
        or len(roots["candidates"]) > 2000
        or not isinstance(roots.get("diagnostics"), list)
        or len(roots["diagnostics"]) > 10_000
    ):
        raise AnalysisFailed("invalid_scan_result")
    lines = {
        source.file_path: max(1, len(source.content.splitlines())) for source in sources
    }
    paths = set()
    for candidate in roots["candidates"]:
        if (
            not isinstance(candidate, dict)
            or set(candidate) != {"file_path", "module", "reason", "source_refs"}
            or not isinstance(candidate.get("module"), str)
            or candidate.get("reason")
            not in {"static_urlpatterns", "literal_root_urlconf"}
            or not isinstance(candidate.get("source_refs"), list)
            or not candidate["source_refs"]
            or candidate.get("file_path") not in lines
            or not candidate["file_path"].endswith(".py")
            or candidate["file_path"] in paths
        ):
            raise AnalysisFailed("invalid_scan_result")
        paths.add(candidate["file_path"])
    if roots.get("selected_root") is not None and roots["selected_root"] not in paths:
        raise AnalysisFailed("invalid_scan_result")
    if (roots["status"] == "selected") != (roots["selected_root"] is not None) or (
        roots["status"] == "no_root"
    ) != (not paths):
        raise AnalysisFailed("invalid_scan_result")
    knowledge = value["knowledge"]
    if (
        not isinstance(knowledge, dict)
        or set(knowledge)
        != {
            "rule_version",
            "python_version",
            "hits",
            "packages",
            "declarations",
            "diagnostics",
            "coverage",
        }
        or not isinstance(knowledge.get("rule_version"), str)
        or not isinstance(knowledge.get("python_version"), str)
        or not isinstance(knowledge.get("coverage"), dict)
    ):
        raise AnalysisFailed("invalid_scan_result")
    for key in ("hits", "packages", "diagnostics", "declarations"):
        if not isinstance(knowledge.get(key), list) or len(knowledge[key]) > (
            2000 if key == "declarations" else 10_000
        ):
            raise AnalysisFailed("invalid_scan_result")

    def inspect(item: Any) -> None:
        if isinstance(item, dict):
            if (
                "source_ref" in item
                and item["source_ref"] is not None
                and (
                    not isinstance(item["source_ref"], dict)
                    or set(item["source_ref"])
                    != {"snapshot_id", "file_path", "start_line", "end_line"}
                )
            ):
                raise AnalysisFailed("invalid_scan_reference")
            for key in ("source_refs", "usage_refs"):
                if key in item and (
                    not isinstance(item[key], list)
                    or any(
                        not isinstance(ref, dict)
                        or set(ref)
                        != {"snapshot_id", "file_path", "start_line", "end_line"}
                        for ref in item[key]
                    )
                ):
                    raise AnalysisFailed("invalid_scan_reference")
            if set(item) == {"snapshot_id", "file_path", "start_line", "end_line"}:
                if (
                    item["snapshot_id"] != snapshot_id
                    or item["file_path"] not in lines
                    or type(item["start_line"]) is not int
                    or type(item["end_line"]) is not int
                    or not 1
                    <= item["start_line"]
                    <= item["end_line"]
                    <= lines[item["file_path"]]
                ):
                    raise AnalysisFailed("invalid_scan_reference")
            for child in item.values():
                inspect(child)
        elif isinstance(item, list):
            for child in item:
                inspect(child)

    inspect(value)
    return value


def run_source_scan(snapshot_id: str, sources: list[Source]) -> dict[str, Any]:
    payload = json.dumps(
        {"snapshot_id": snapshot_id, "sources": [asdict(source) for source in sources]},
        ensure_ascii=False,
    ).encode("utf-8")
    if len(payload) > 128 * 1024 * 1024:
        raise AnalysisFailed("input_limit")
    try:
        with TemporaryFile() as output:
            process = subprocess.run(
                [sys.executable, "-I", str(Path(__file__).with_name("scan_worker.py"))],
                input=payload,
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=PARSER_TIMEOUT_SECONDS,
                check=False,
            )
            output.seek(0)
            content = output.read(MAX_OUTPUT_BYTES + 1)
        if len(content) > MAX_OUTPUT_BYTES:
            raise AnalysisFailed("output_limit")
        if process.returncode != 0:
            raise AnalysisFailed("scan_process_failed")
        return validate_scan(json.loads(content), snapshot_id, sources)
    except subprocess.TimeoutExpired:
        raise AnalysisFailed("scan_timeout") from None
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise AnalysisFailed("scan_protocol_or_io_failed") from None
