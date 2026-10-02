"""固定的隔离解析入口，只读取协议文本，绝不导入待分析项目。"""

import json
import resource
import sys
from pathlib import Path

# -I 禁用环境和当前目录搜索；只加入受信任的工作台源码目录。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.analysis.parser import analyze  # noqa: E402
from apps.analysis.types import (  # noqa: E402
    MAX_OUTPUT_BYTES,
    PARSER_TIMEOUT_SECONDS,
    AnalysisFailed,
    Source,
)


def main() -> int:
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(
        resource.RLIMIT_CPU, (PARSER_TIMEOUT_SECONDS, PARSER_TIMEOUT_SECONDS)
    )
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    try:
        payload = json.load(sys.stdin)
        result = analyze(
            payload["snapshot_id"],
            [Source(**item) for item in payload["sources"]],
            payload["root_urlconf"],
            payload["skipped_files"],
        )
        encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
        if len(encoded) > MAX_OUTPUT_BYTES:
            raise AnalysisFailed("output_limit")
        sys.stdout.write(encoded)
    except AnalysisFailed as exc:
        sys.stdout.write(json.dumps({"failure": exc.reason}))
        return 2
    except Exception:
        # 子进程边界不输出 traceback、源码行或文件名；父进程持久化整体失败。
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
