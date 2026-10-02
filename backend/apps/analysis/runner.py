import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryFile

from apps.analysis.protocol import validate_result
from apps.analysis.types import (
    MAX_OUTPUT_BYTES,
    PARSER_TIMEOUT_SECONDS,
    AnalysisFailed,
    AnalysisResult,
    Source,
)


def run_parser(
    snapshot_id: str, sources: list[Source], root_urlconf: str, skipped_files: int
) -> AnalysisResult:
    payload = json.dumps(
        {
            "snapshot_id": snapshot_id,
            "root_urlconf": root_urlconf,
            "sources": [asdict(s) for s in sources],
            "skipped_files": skipped_files,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    if len(payload) > 128 * 1024 * 1024:
        raise AnalysisFailed("input_limit")
    try:
        with TemporaryFile() as output:
            process = subprocess.run(
                [sys.executable, "-I", str(Path(__file__).with_name("worker.py"))],
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
        if process.returncode not in {0, 2}:
            raise AnalysisFailed("parser_process_failed")
        decoded = json.loads(content)
        if process.returncode == 2:
            reasons = {
                "root_urlconf_unavailable",
                "ast_resource_limit",
                "ast_node_limit",
                "diagnostic_limit",
                "endpoint_limit",
                "output_limit",
            }
            if (
                isinstance(decoded, dict)
                and isinstance(decoded.get("failure"), str)
                and decoded["failure"] in reasons
            ):
                raise AnalysisFailed(decoded["failure"])
            raise AnalysisFailed("parser_process_failed")
        return validate_result(decoded, snapshot_id, sources)
    except subprocess.TimeoutExpired:
        raise AnalysisFailed("parser_timeout") from None
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise AnalysisFailed("parser_protocol_or_io_failed") from None
