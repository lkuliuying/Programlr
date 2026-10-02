"""在项目目录内准备固定版本工具，校验官方摘要，不修改全局环境。"""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
UV_VERSION = "0.12.19"


def read_url(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read(4 * 1024 * 1024)


def download(
    url: str,
    destination: Path,
    expected_hash: str,
    *,
    expected_size: int | None = None,
    timeout_seconds: float = 300,
    allowed_host: str | None = None,
) -> None:
    if destination.is_file():
        with destination.open("rb") as existing:
            if hashlib.file_digest(
                existing, "sha256"
            ).hexdigest() == expected_hash and (
                expected_size is None or destination.stat().st_size == expected_size
            ):
                print(f"复用已校验文件：{destination.name}", flush=True)
                return
    partial = destination.with_suffix(destination.suffix + ".part")
    if partial.is_file():
        with partial.open("rb") as existing:
            partial_hash = hashlib.file_digest(existing, "sha256").hexdigest()
        if partial_hash == expected_hash and (
            expected_size is None or partial.stat().st_size == expected_size
        ):
            partial.replace(destination)
            print(f"复用已完整校验分片：{destination.name}", flush=True)
            return
    if (
        expected_size is not None
        and partial.exists()
        and partial.stat().st_size >= expected_size
    ):
        partial.unlink()
    started = time.monotonic()
    size = partial.stat().st_size if partial.exists() else 0
    request = urllib.request.Request(url)
    if size:
        request.add_header("Range", f"bytes={size}-")
    with urllib.request.urlopen(request, timeout=30) as response:
        if allowed_host is not None:
            final_url = urlsplit(response.geturl())
            if final_url.scheme != "https" or final_url.hostname != allowed_host:
                raise RuntimeError("下载重定向离开已允许的官方来源")
        if response.status == 206:
            content_range = response.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
            if match is None or int(match[1]) != size or int(match[2]) < size:
                raise RuntimeError("续传响应起始位置不正确")
            if int(match[2]) >= int(match[3]) or (
                expected_size is not None and int(match[3]) != expected_size
            ):
                raise RuntimeError("续传响应总大小不正确")
            digest = hashlib.sha256()
            if size:
                with partial.open("rb") as existing:
                    digest = hashlib.file_digest(existing, "sha256")
            mode = "ab"
        elif response.status == 200:
            # 官方服务器不支持续传时重新下载，绝不拼接完整响应造成损坏。
            size = 0
            digest = hashlib.sha256()
            mode = "wb"
        else:
            raise RuntimeError("工具下载收到非预期 HTTP 状态")
        with partial.open(mode) as output:
            progress = size // (1024 * 1024)
            while chunk := response.read(64 * 1024):
                if time.monotonic() - started > timeout_seconds:
                    raise TimeoutError(
                        "工具下载超过 300 秒；已保留分片，可再次运行续传"
                    )
                if expected_size is not None and size + len(chunk) > expected_size:
                    raise RuntimeError("下载内容超过锁定大小")
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
                if size // (1024 * 1024) > progress:
                    progress = size // (1024 * 1024)
                    print(f"下载 {destination.name}：{progress} MiB", flush=True)
    if expected_size is not None and size != expected_size:
        raise EOFError("下载未完整结束；已保留分片")
    if digest.hexdigest() != expected_hash:
        # 摘要错误的临时内容不能进入下一次续传，也不能替换已发布工具。
        partial.unlink()
        raise RuntimeError(f"官方 SHA-256 校验失败：{destination.name}")
    partial.replace(destination)
    print(f"SHA-256 校验通过：{destination.name}", flush=True)


def prepare_uv(target: str) -> tuple[Path, str]:
    downloads = RUNTIME / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    tools = RUNTIME / "tools"
    tools.mkdir(exist_ok=True)
    metadata = json.loads(read_url(f"https://pypi.org/pypi/uv/{UV_VERSION}/json"))
    suffix = {
        "windows": "py3-none-win_amd64.whl",
        "linux": "py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    }[target]
    wheels = [
        item
        for item in metadata["urls"]
        if item["filename"] == f"uv-{UV_VERSION}-{suffix}"
    ]
    if len(wheels) != 1:
        raise RuntimeError("未找到唯一的 uv 目标平台官方分发包")
    wheel = wheels[0]
    wheel_path = downloads / wheel["filename"]
    download(wheel["url"], wheel_path, wheel["digests"]["sha256"])
    uv_directory = tools / f"uv-{UV_VERSION}{'-linux' if target == 'linux' else ''}"
    uv_directory.mkdir(exist_ok=True)
    executable_name = "uv.exe" if target == "windows" else "uv"
    with zipfile.ZipFile(wheel_path) as archive:
        executables = [
            name for name in archive.namelist() if name.endswith(f"/{executable_name}")
        ]
        if len(executables) != 1:
            raise RuntimeError("uv 分发包中的可执行文件不唯一")
        uv_path = uv_directory / executable_name
        executable = archive.read(executables[0])
        # Windows 不允许覆盖运行中的程序；完整内容相同时直接复用。
        if not uv_path.is_file() or uv_path.read_bytes() != executable:
            uv_path.write_bytes(executable)
    (uv_directory / "verified.json").write_text(
        json.dumps(
            {
                "version": UV_VERSION,
                "wheel_sha256": wheel["digests"]["sha256"],
                "executable_sha256": hashlib.sha256(executable).hexdigest(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return uv_path, wheel["digests"]["sha256"]


def main() -> None:
    parser = argparse.ArgumentParser(description="准备项目内固定版本工具并校验官方摘要")
    parser.add_argument(
        "--linux-uv", action="store_true", help="只准备 Linux 容器所需的 uv"
    )
    arguments = parser.parse_args()
    if arguments.linux_uv:
        prepare_uv("linux")
        return
    if platform.system() != "Windows" or platform.machine().lower() not in {
        "amd64",
        "x86_64",
    }:
        raise RuntimeError("默认准备入口仅支持 Windows x64；Linux 使用临时验证容器")
    uv, uv_hash = prepare_uv("windows")
    downloads = RUNTIME / "downloads"
    tools = RUNTIME / "tools"
    subprocess.run([str(uv), "--version"], check=True, timeout=15)

    node_version = (ROOT / "frontend/.node-version").read_text().strip()
    node_name = f"node-v{node_version}-win-x64"
    node_file = f"{node_name}.zip"
    base_url = f"https://nodejs.org/dist/v{node_version}"
    checksums = read_url(f"{base_url}/SHASUMS256.txt").decode("utf-8")
    node_hashes = [
        line.split()[0]
        for line in checksums.splitlines()
        if line.split()[-1] == node_file
    ]
    if len(node_hashes) != 1:
        raise RuntimeError("Node 官方校验记录不唯一")
    node_archive = downloads / node_file
    download(f"{base_url}/{node_file}", node_archive, node_hashes[0])
    with zipfile.ZipFile(node_archive) as archive:
        for name in archive.namelist():
            parts = Path(name).parts
            if not parts or parts[0] != node_name or ".." in parts:
                raise RuntimeError("Node 分发包包含越界路径")
        archive.extractall(tools)
    subprocess.run(
        [str(tools / node_name / "node.exe"), "--version"], check=True, timeout=15
    )

    environment = os.environ.copy()
    environment["UV_CACHE_DIR"] = str(RUNTIME / "uv-cache")
    environment["UV_PYTHON_INSTALL_DIR"] = str(RUNTIME / "python")
    python_version = (ROOT / "backend/.python-version").read_text().strip()
    subprocess.run(
        [str(uv), "python", "install", python_version, "--no-bin"],
        env=environment,
        check=True,
        timeout=600,
    )
    evidence = {
        "uv": {"version": UV_VERSION, "sha256": uv_hash},
        "node": {"version": node_version, "sha256": node_hashes[0]},
        "python": {"version": python_version, "installer": f"uv {UV_VERSION}"},
    }
    (downloads / "verified-tools.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
