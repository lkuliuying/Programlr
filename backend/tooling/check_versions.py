"""核对实际解释器、直接依赖与独立锁文件的一致性。"""

import json
import platform
import re
import tomllib
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_versions() -> dict[str, str]:
    expected_python = (ROOT / ".python-version").read_text().strip()
    if platform.python_version() != expected_python:
        raise RuntimeError("实际 Python 与 .python-version 不一致")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {item["name"]: item.get("version") for item in lock["package"]}
    requirements = (
        project["project"]["dependencies"] + project["dependency-groups"]["dev"]
    )
    observed = {"python": platform.python_version()}
    for requirement in requirements:
        match = re.fullmatch(r"([\w-]+)(?:\[[\w,-]+\])?==([\d.]+)", requirement)
        if match is None:
            raise RuntimeError("直接依赖必须使用精确稳定版本")
        name, expected = match.groups()
        actual = version(name)
        if actual != expected or locked.get(name) != expected:
            raise RuntimeError(f"依赖版本不一致：{name}")
        observed[name] = actual
    return observed


if __name__ == "__main__":
    print(json.dumps(check_versions(), ensure_ascii=False, sort_keys=True))
