"""从实现重新导出并只读核对契约、接口表和类型，不连接业务数据库。"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ("workbench", Path("."), "apps/jobs/tests/test_contract.py"),
    ("task-board", Path("examples/task-board"), "apps/tasks/tests/test_contract.py"),
)


def require_equal(actual: str, expected: str, label: str) -> None:
    if actual.replace("\r\n", "\n") != expected.replace("\r\n", "\n"):
        raise ValueError(f"{label} 已漂移；请审阅后重新生成，不会自动覆盖。")


def verify_catalog(schema: dict[str, Any], catalog: str, service: str) -> None:
    documented = {
        (method.lower(), path, operation)
        for name, method, path, operation in re.findall(
            r"^\| (workbench|task-board|lab-board) \| (GET|POST|PATCH) \| `([^`]+)` \| `([^`]+)` \|",
            catalog,
            re.MULTILINE,
        )
        if name == service
    }
    implemented = {
        (method, path, operation["operationId"])
        for path, methods in schema["paths"].items()
        for method, operation in methods.items()
        if method in {"get", "post", "put", "patch", "delete", "head", "options"}
    }
    if not documented or implemented != documented:
        raise ValueError(f"{service} 的已实现接口表与实际 Schema 不一致。")


def run(command: list[str], cwd: Path) -> None:
    print(f"[{cwd.relative_to(ROOT)}] {' '.join(command)}", flush=True)
    # 使用参数列表和有界期限；子进程继承控制台，避免积累无界输出。
    subprocess.run(command, cwd=cwd, check=True, timeout=120)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--node", default="node", help="已安装的项目固定 Node 可执行文件"
    )
    args = parser.parse_args()
    node = str(Path(args.node).resolve()) if Path(args.node).exists() else args.node
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    catalog = (ROOT / "docs/api-catalog.md").read_text(encoding="utf-8")
    try:
        with TemporaryDirectory(prefix="contract-check-", dir=runtime) as temporary:
            for service, relative, test in TARGETS:
                base = ROOT / relative
                backend, frontend = base / "backend", base / "frontend"
                exported = Path(temporary) / f"{service}.yaml"
                run(
                    [
                        sys.executable,
                        "manage.py",
                        "spectacular",
                        "--settings=config.settings.test",
                        "--file",
                        str(exported),
                        "--validate",
                        "--fail-on-warn",
                    ],
                    backend,
                )
                content = exported.read_text(encoding="utf-8")
                require_equal(
                    content,
                    (base / "contracts/openapi.yaml").read_text(encoding="utf-8"),
                    f"{service} OpenAPI",
                )
                verify_catalog(yaml.safe_load(content), catalog, service)
                run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        test,
                        "--ds=config.settings.test",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                    ],
                    backend,
                )
                if service == "workbench":
                    run(
                        [
                            sys.executable,
                            "-m",
                            "pytest",
                            "apps/projects/tests/test_contract.py",
                            "apps/analysis/tests/test_contract.py",
                            "apps/explanations/tests/test_contract.py",
                            "--ds=config.settings.test",
                            "-q",
                            "-p",
                            "no:cacheprovider",
                        ],
                        backend,
                    )
                run([node, "tooling/generate-api-types.mjs", "--check"], frontend)
                run([node, "node_modules/typescript/bin/tsc", "--noEmit"], frontend)
            lab_schema = Path(temporary) / "lab-board.yaml"
            run(
                [
                    sys.executable,
                    "manage.py",
                    "spectacular",
                    "--settings=config.settings.labs_test",
                    "--file",
                    str(lab_schema),
                    "--validate",
                    "--fail-on-warn",
                ],
                ROOT / "examples/task-board/backend",
            )
            content = lab_schema.read_text(encoding="utf-8")
            require_equal(
                content,
                (ROOT / "examples/task-board/contracts/labs-openapi.yaml").read_text(
                    encoding="utf-8"
                ),
                "lab-board OpenAPI",
            )
            verify_catalog(yaml.safe_load(content), catalog, "lab-board")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"契约检查失败：{exc}", file=sys.stderr)
        return 1
    print("三份服务契约及接口表一致，两套前端类型与实现一致。")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    raise SystemExit(main())
