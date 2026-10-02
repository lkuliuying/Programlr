import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryFile

from apps.analysis.diffs.protocol import validate_comparison
from apps.analysis.diffs.types import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    TIMEOUT_SECONDS,
    ComparisonData,
    ComparisonFailed,
    ComparisonInput,
)


def run_comparison(payload: ComparisonInput) -> ComparisonData:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        raise ComparisonFailed("input_limit")
    try:
        with TemporaryFile() as output:
            process = subprocess.run(
                [sys.executable, "-I", str(Path(__file__).with_name("worker.py"))],
                input=encoded,
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
            output.seek(0)
            raw = output.read(MAX_OUTPUT_BYTES + 1)
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ComparisonFailed("output_limit")
        value = json.loads(raw)
        if (
            process.returncode == 2
            and isinstance(value, dict)
            and value.get("failure")
            in {
                "input_limit",
                "output_limit",
                "file_count_limit",
                "file_line_limit",
                "file_diff_limit",
            }
        ):
            raise ComparisonFailed(value["failure"])
        if process.returncode:
            raise ComparisonFailed("comparison_process_failed")
        sides = [payload["base_analysis"], payload["target_analysis"]]
        return validate_comparison(
            value,
            payload["comparison_id"],
            payload["base_snapshot_id"],
            payload["target_snapshot_id"],
            (
                sides[0]["version"]["analysis_id"] if sides[0] else None,
                sides[1]["version"]["analysis_id"] if sides[1] else None,
            ),
            (
                sides[0]["graph"] if sides[0] else None,
                sides[1]["graph"] if sides[1] else None,
            ),
        )
    except subprocess.TimeoutExpired:
        raise ComparisonFailed("comparison_timeout") from None
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ComparisonFailed("comparison_protocol_or_io_failed") from None
