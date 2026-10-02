"""通过固定回环地址验证可信示例，不读取配置秘密或调用导入项目。"""

import argparse
import http.cookiejar
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5174"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restart",
        action="store_true",
        help="重启示例 API 和数据库验证持久化，不影响工作台",
    )
    args = parser.parse_args()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    checks: dict[str, bool] = {}

    def request(
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        key: str | None = None,
        token: str = "",
        origin: str = ORIGIN,
    ) -> tuple[int, Any]:
        headers = {"Origin": origin}
        if payload is not None:
            headers.update(
                {
                    "Content-Type": "application/json",
                    "Idempotency-Key": key or str(uuid.uuid4()),
                    "X-CSRFToken": token,
                }
            )
        req = urllib.request.Request(
            ORIGIN + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
        )
        try:
            response = opener.open(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def check(name: str, condition: bool) -> None:
        checks[name] = condition
        if not condition:
            raise AssertionError(f"示例验收失败：{name}")

    _, csrf = request("/api/v1/csrf/")
    token = csrf["csrf_token"]
    _, initial = request("/api/v1/tasks/")
    count = initial["count"]
    key = str(uuid.uuid4())
    title = "HTTP 验收 " + uuid.uuid4().hex[:8]
    observations = []
    for label, payload, expected, increment in (
        ("normal", {"title": title}, 201, 1),
        ("missing", {}, 400, 0),
        ("empty", {"title": ""}, 400, 0),
        ("whitespace", {"title": " \t\n "}, 400, 0),
    ):
        status, body = request(
            "/api/v1/tasks/",
            payload,
            key=key if label == "normal" else None,
            token=token,
        )
        _, page = request("/api/v1/tasks/")
        check(label + "_status", status == expected)
        check(label + "_writes", page["count"] - count == increment)
        observations.append(
            {
                "case": label,
                "input": payload,
                "http_status": status,
                "response": body,
                "writes": page["count"] - count,
            }
        )
        count = page["count"]
    task_id = observations[0]["response"]["id"]
    status, replay = request("/api/v1/tasks/", {"title": title}, key=key, token=token)
    check("replay", status == 200 and replay["id"] == task_id)
    status, _ = request(
        "/api/v1/tasks/", {"title": title + " conflict"}, key=key, token=token
    )
    check("conflict", status == 409)
    status, _ = request("/api/v1/tasks/", {"title": title})
    check("csrf_rejected", status == 403)
    status, _ = request(
        "/api/v1/tasks/", {"title": title}, token=token, origin="http://127.0.0.1:5173"
    )
    check("cross_origin_rejected", status == 403)
    _, final = request("/api/v1/tasks/")
    check("no_extra_writes", final["count"] == count)
    check("record_readable", any(item["id"] == task_id for item in final["results"]))
    if args.restart:
        subprocess.run(
            ["docker", "compose", "restart", "task-board-postgres", "task-board-api"],
            cwd=ROOT,
            check=True,
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 45
        while True:
            try:
                status, page = request("/api/v1/tasks/")
                if status == 200:
                    break
            # 重启窗口内代理可能返回 HTML 错误页；只在此有界恢复检查中等待。
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("示例重启后未在期限内恢复。")
            time.sleep(1)
        check(
            "restart_persistence",
            page["count"] == count
            and any(item["id"] == task_id for item in page["results"]),
        )
    report = {
        "example_version": "task-board/1.0.0",
        "checks": checks,
        "observations": observations,
        "succeeded": True,
    }
    output = ROOT / ".runtime/m1-t03-http-verification.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"示例 HTTP 检查通过：{len(checks)} 项；真实响应与写入差值已保存。")


if __name__ == "__main__":
    main()
