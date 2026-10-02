"""按独立锁文件准备官方 wheel；下载与离线安装分别计时。"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from prepare_toolchain import ROOT, RUNTIME, download

PYTHON_IMAGE = (
    "python@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26"
)
WHEELHOUSE = RUNTIME / "backend-wheelhouse"


def validate_artifact(item: dict) -> str:
    """只接受锁文件中的官方 HTTPS 分发及完整 SHA-256。"""
    url = urlsplit(item["url"])
    name = url.path.rsplit("/", 1)[-1]
    digest = item["hash"]
    if (
        url.scheme != "https"
        or url.hostname != "files.pythonhosted.org"
        or url.username is not None
        or url.password is not None
        or url.port not in (None, 443)
        or url.query
        or url.fragment
        or not name.endswith(".whl")
        or any(character in name for character in ("\\", "%", ":"))
        or not digest.startswith("sha256:")
        or len(digest) != 71
        or any(c not in "0123456789abcdef" for c in digest[7:])
        or not isinstance(item["size"], int)
        or item["size"] <= 0
    ):
        raise ValueError("锁定 wheel 的来源、大小或摘要不合法")
    return name


def fetch_artifact(item: dict, deadline: float) -> Path:
    name = validate_artifact(item)
    destination = WHEELHOUSE / "downloads" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("下载准备超过 1800 秒")
        command = [
            sys.executable,
            "-X",
            "utf8",
            str(Path(__file__).resolve()),
            "--download-one",
            json.dumps(item),
        ]
        try:
            result = subprocess.run(command, timeout=min(300, remaining), check=False)
            if result.returncode == 0:
                return destination
            if result.returncode != 75:
                raise RuntimeError(f"wheel 校验失败：{name}")
        except subprocess.TimeoutExpired:
            # subprocess.run 会终止并等待本次下载进程；下一次只续传已写入的内容。
            print(f"下载超时：{name}，尝试 {attempt}/3", flush=True)
    raise TimeoutError(f"下载已耗尽三次尝试：{name}")


def reference_tags(target: str, packaging_wheel: Path, deadline: float) -> list[str]:
    expected = (ROOT / "backend/.python-version").read_text().strip()
    source = (
        "import sys,json,platform;sys.path.insert(0,sys.argv[1]);"
        "from packaging.tags import sys_tags;"
        "print(json.dumps({'python':platform.python_version(),'tags':[str(t) for t in sys_tags()]}))"
    )
    timeout = min(60, deadline - time.monotonic())
    if timeout <= 0:
        raise TimeoutError("下载准备超过 1800 秒")
    if target == "windows":
        env = os.environ.copy()
        env["UV_PYTHON_INSTALL_DIR"] = str(RUNTIME / "python")
        env["UV_CACHE_DIR"] = str(RUNTIME / "uv-cache")
        uv = RUNTIME / "tools/uv-0.12.19/uv.exe"
        found = subprocess.run(
            [str(uv), "python", "find", "--managed-python", expected],
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        command = [found.stdout.strip(), "-c", source, str(packaging_wheel)]
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout
        )
    else:
        docker = (
            Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "Docker/Docker/resources/bin/docker.exe"
        )
        name = f"m1-wheel-tags-{uuid.uuid4().hex}"
        command = [
            str(docker),
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--cpus",
            "2",
            "--memory",
            "2g",
            "--pids-limit",
            "256",
            "--mount",
            f"type=bind,source={packaging_wheel.parent},target=/wheels,readonly",
            PYTHON_IMAGE,
            "python",
            "-c",
            source,
            f"/wheels/{packaging_wheel.name}",
        ]
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=timeout
            )
        finally:
            subprocess.run(
                [str(docker), "container", "rm", "--force", name],
                capture_output=True,
                timeout=15,
                check=False,
            )
    evidence = json.loads(result.stdout)
    if evidence["python"] != expected:
        raise RuntimeError("参考解释器版本与记录不一致")
    return evidence["tags"]


def choose_wheels(packages: list[dict], tags: list[str]) -> list[dict]:
    """使用已校验 packaging 的公共解析器，按参考解释器优先级选择分发。"""
    from packaging.utils import canonicalize_name, parse_wheel_filename

    ranking = {tag: index for index, tag in enumerate(tags)}
    selected = []
    for package in packages:
        if "virtual" in package.get("source", {}):
            continue
        if package.get("source") != {"registry": "https://pypi.org/simple"}:
            raise ValueError("不支持非官方锁定来源")
        candidates = []
        for wheel in package.get("wheels", []):
            name = validate_artifact(wheel)
            distribution, version, _, wheel_tags = parse_wheel_filename(name)
            if (
                distribution != canonicalize_name(package["name"])
                or str(version) != package["version"]
            ):
                raise ValueError("wheel 名称或版本不匹配")
            ranks = [ranking[str(tag)] for tag in wheel_tags if str(tag) in ranking]
            if ranks:
                candidates.append((min(ranks), name, wheel))
        if not candidates:
            raise RuntimeError(f"参考环境没有可用 wheel：{package['name']}")
        selected.append(min(candidates, key=lambda candidate: candidate[:2])[2])
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="准备锁定的后端 wheel，不安装依赖")
    parser.add_argument(
        "--platform", choices=("windows", "linux", "all"), default="all"
    )
    parser.add_argument("--download-one", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.download_one:
        item = json.loads(arguments.download_one)
        name = validate_artifact(item)
        try:
            download(
                item["url"],
                WHEELHOUSE / "downloads" / name,
                item["hash"][7:],
                expected_size=item["size"],
                allowed_host="files.pythonhosted.org",
            )
        except (TimeoutError, OSError, EOFError) as error:
            print(f"下载暂未完成：{name}（{type(error).__name__}）", flush=True)
            raise SystemExit(75) from None
        return
    started = time.monotonic()
    deadline = started + 1800
    lock_path = ROOT / "backend/uv.lock"
    lock_hash = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    packages = tomllib.loads(lock_path.read_text(encoding="utf-8"))["package"]
    bootstrap = next(p for p in packages if p["name"] == "packaging")
    universal = [
        w for w in bootstrap["wheels"] if w["url"].endswith("-py3-none-any.whl")
    ]
    if len(universal) != 1:
        raise RuntimeError("packaging 引导分发不唯一")
    packaging_wheel = fetch_artifact(universal[0], deadline)
    sys.path.insert(0, str(packaging_wheel))
    targets = (
        ("windows", "linux") if arguments.platform == "all" else (arguments.platform,)
    )
    selections = {
        target: choose_wheels(
            packages, reference_tags(target, packaging_wheel, deadline)
        )
        for target in targets
    }
    unique = {wheel["url"]: wheel for wheels in selections.values() for wheel in wheels}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(fetch_artifact, item, deadline) for item in unique.values()
        ]
        for future in futures:
            future.result()
    for target, wheels in selections.items():
        if time.monotonic() >= deadline:
            raise TimeoutError("下载准备超过 1800 秒")
        directory = WHEELHOUSE / target / lock_hash
        directory.mkdir(parents=True, exist_ok=True)
        for item in wheels:
            name = validate_artifact(item)
            source = WHEELHOUSE / "downloads" / name
            if (
                source.stat().st_size != item["size"]
                or hashlib.sha256(source.read_bytes()).hexdigest() != item["hash"][7:]
            ):
                raise RuntimeError("下载集合完整性检查失败")
            shutil.copyfile(source, directory / name)
        (directory / "manifest.json").write_text(
            json.dumps(
                {"lock_sha256": lock_hash, "platform": target, "wheels": wheels},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if hashlib.sha256(lock_path.read_bytes()).hexdigest() != lock_hash:
        raise RuntimeError("准备过程中锁文件发生变化")
    if time.monotonic() >= deadline:
        raise TimeoutError("下载准备超过 1800 秒")
    print(
        json.dumps(
            {
                "succeeded": True,
                "platforms": list(targets),
                "unique_wheels": len(unique),
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "lock_sha256": lock_hash,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
