"""验证本项目真实 HTTP 链路；凭据和 CSRF 令牌只保留在内存中。"""

import argparse
import http.cookiejar
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5173"
RESULTS: list[dict[str, object]] = []


def record(name: str, passed: bool) -> None:
    RESULTS.append({"check": name, "passed": passed})
    print(f"{name}: {'通过' if passed else '失败'}", flush=True)
    if not passed:
        raise RuntimeError(f"检查未通过：{name}")


def docker(*arguments: str) -> str:
    executable = shutil.which("docker")
    if executable is None:
        candidate = Path("C:/Program Files/Docker/Docker/resources/bin/docker.exe")
        executable = str(candidate) if candidate.exists() else None
    if executable is None:
        raise RuntimeError("未找到 Docker CLI。")
    result = subprocess.run(
        [executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Docker 操作失败，退出码 {result.returncode}；请检查本项目服务状态。"
        )
    return result.stdout


def compose(*arguments: str) -> str:
    return docker("compose", *arguments)


class Client:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
        self.token = ""

    def request(
        self,
        path: str,
        *,
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any, Any]:
        if not path.startswith("/api/v1/") or path.startswith("//"):
            raise ValueError("拒绝非工作台接口路径。")
        fields = {"Origin": ORIGIN}
        if key:
            fields.update(
                {
                    "Content-Type": "application/json",
                    "Idempotency-Key": key,
                    "X-CSRFToken": self.token,
                }
            )
        fields.update(headers or {})
        request = urllib.request.Request(
            ORIGIN + path, data=b"{}" if key else None, headers=fields
        )
        try:
            response = self.opener.open(request, timeout=12)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read(65536)
            data = (
                json.loads(content)
                if "application/json" in response.headers.get("Content-Type", "")
                else None
            )
            return response.status, data, response.headers

    def csrf(self) -> None:
        status, data, headers = self.request("/api/v1/csrf/")
        if status != 200 or "no-store" not in headers.get("Cache-Control", ""):
            raise RuntimeError("CSRF 初始化失败。")
        self.token = data["csrf_token"]


def wait_job(
    client: Client, path: str, expected: str, seconds: int = 35
) -> dict[str, Any]:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        status, data, _ = client.request(path)
        if status == 200 and data["status"] in ("succeeded", "failed"):
            record(f"任务收敛至 {expected}", data["status"] == expected)
            return dict(data)
        time.sleep(1)
    raise RuntimeError("任务未在验收期限内收敛。")


def wait_api() -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if Client().request("/api/v1/jobs/")[0] == 200:
                return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(1)
    raise RuntimeError("API 未在恢复期限内就绪。")


def check_bindings() -> None:
    ids = compose("ps", "-q").split()
    containers = json.loads(docker("inspect", *ids))
    mapped = []
    for container in containers:
        service = container["Config"]["Labels"]["com.docker.compose.service"]
        for entries in container["NetworkSettings"]["Ports"].values():
            for entry in entries or []:
                mapped.append((service, entry["HostIp"], entry["HostPort"]))
    record("仅前端发布回环入口", mapped == [("frontend", "127.0.0.1", "5173")])
    addresses = {
        entry[4][0]
        for entry in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    }
    addresses = {address for address in addresses if not address.startswith("127.")}
    if not addresses:
        raise RuntimeError("当前无非回环地址，AT-24 的实连检查未完成。")
    for address in addresses:
        with socket.socket() as connection:
            connection.settimeout(2)
            record("非回环连接被拒绝", connection.connect_ex((address, 5173)) != 0)


def check_http(client: Client) -> str:
    client.csrf()
    for name, headers in (
        ("缺失 CSRF", {"X-CSRFToken": ""}),
        ("错误 CSRF", {"X-CSRFToken": "invalid"}),
        ("缺失 Origin", {"Origin": ""}),
        ("跨站 Origin", {"Origin": "https://untrusted.example"}),
        ("不同端口 Origin", {"Origin": "http://127.0.0.1:5174"}),
        ("非法 Host", {"Host": "untrusted.example"}),
        (
            "伪造转发头",
            {
                "Origin": "https://untrusted.example",
                "X-Forwarded-Host": "127.0.0.1:5173",
                "X-Forwarded-Proto": "http",
            },
        ),
    ):
        status, _, _ = client.request(
            "/api/v1/system-checks/", key=str(uuid.uuid4()), headers=headers
        )
        record(f"匿名写入拒绝：{name}", status == 403)
    key = str(uuid.uuid4())
    status, data, headers = client.request("/api/v1/system-checks/", key=key)
    record("合法匿名提交已接收", status == 202)
    path = headers["Location"]
    duplicate, replay, _ = client.request("/api/v1/system-checks/", key=key)
    record("同键重放返回原任务", duplicate == 200 and data["id"] == replay["id"])
    job = wait_job(client, path, "succeeded")
    status, result, _ = client.request(job["result_url"])
    record(
        "实际 Worker 结果已持久化",
        status == 200
        and result["job_id"] == job["id"]
        and result["worker"] == "passed",
    )
    refreshed = Client().request(path)
    record(
        "新客户端可恢复任务记录",
        refreshed[0] == 200 and refreshed[1]["status"] == "succeeded",
    )
    return path


def check_faults(client: Client, successful_path: str) -> None:
    try:
        compose("stop", "redis")
        key = str(uuid.uuid4())
        status, _, headers = client.request("/api/v1/system-checks/", key=key)
        record("真实 Redis 停机返回 503", status == 503)
        failed = client.request(headers["Location"])
        record(
            "队列失败记录可读",
            failed[0] == 200 and failed[1]["error"]["code"] == "QUEUE_UNAVAILABLE",
        )
        status, replay, _ = client.request("/api/v1/system-checks/", key=key)
        record("队列失败重放不会重投", status == 200 and replay["status"] == "failed")
        compose("start", "redis")
        compose("stop", "worker")
        status, _, headers = client.request(
            "/api/v1/system-checks/", key=str(uuid.uuid4())
        )
        record("Worker 停机时任务保留排队记录", status == 202)
        failed = wait_job(client, headers["Location"], "failed")
        record("独立核对进程终结排队超时", failed["error"]["code"] == "QUEUE_TIMEOUT")
        compose("start", "worker")
        time.sleep(3)
        record(
            "迟到投递未覆盖失败终态",
            client.request(headers["Location"])[1]["status"] == "failed",
        )
        compose("stop", "postgres")
        status, data, _ = client.request("/api/v1/jobs/")
        record(
            "真实数据库停机返回可读错误",
            status == 503 and data["code"] == "SERVICE_UNAVAILABLE",
        )
    finally:
        compose("start", "postgres", "redis", "worker")
        wait_api()
    compose("restart", "postgres", "redis", "api", "worker", "reconciler", "frontend")
    wait_api()
    status, data, _ = Client().request(successful_path)
    record(
        "完整服务重启后结果仍可读取", status == 200 and data["status"] == "succeeded"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--faults",
        action="store_true",
        help="先使用 compose.verify.yaml 启动；仅短暂停止本项目服务。",
    )
    arguments = parser.parse_args()
    os.chdir(ROOT)
    completed = False
    try:
        wait_api()
        check_bindings()
        client = Client()
        path = check_http(client)
        if arguments.faults:
            check_faults(client, path)
        completed = True
    finally:
        report = ROOT / ".runtime/m1-t02-http-verification.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "checks": RESULTS,
                    "faults_requested": arguments.faults,
                    "succeeded": completed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
