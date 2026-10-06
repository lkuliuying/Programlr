"""固定源码扫描入口，不加载导入项目或它的依赖。"""

import json
import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.analysis.root_discovery import discover_roots  # noqa: E402
from apps.analysis.types import (  # noqa: E402
    MAX_OUTPUT_BYTES,
    PARSER_TIMEOUT_SECONDS,
    Source,
)
from apps.learning.source_scan import scan_knowledge_facts  # noqa: E402


def main() -> int:
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(
        resource.RLIMIT_CPU, (PARSER_TIMEOUT_SECONDS, PARSER_TIMEOUT_SECONDS)
    )
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    try:
        payload = json.load(sys.stdin)
        sources = [Source(**value) for value in payload["sources"]]
        result = {
            "roots": discover_roots(payload["snapshot_id"], sources),
            "knowledge": scan_knowledge_facts(payload["snapshot_id"], sources),
        }
        encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
        if len(encoded) > MAX_OUTPUT_BYTES:
            return 2
        sys.stdout.write(encoded)
    except Exception:
        # 固定进程边界只返回失败码，源码和依赖异常不进入输出。
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
