"""隔离差异计算入口，导入源码仅作为文本处理。"""

import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apps.analysis.diffs.engine import compare  # noqa: E402
from apps.analysis.diffs.types import (  # noqa: E402
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    TIMEOUT_SECONDS,
    ComparisonFailed,
)


def main() -> int:
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT_SECONDS, TIMEOUT_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ComparisonFailed("input_limit")
        result = compare(json.loads(raw))
        encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise ComparisonFailed("output_limit")
        sys.stdout.write(encoded)
    except ComparisonFailed as error:
        sys.stdout.write(json.dumps({"failure": error.reason}))
        return 2
    except Exception:
        # 进程边界只返回失败，不泄露路径、正文或 traceback。
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
