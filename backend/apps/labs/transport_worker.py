"""只访问固定内网示例；输入不包含地址、脚本或任意路径。"""

import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
import uuid

ORIGIN = "http://127.0.0.1:5174"
TARGET = "http://task-board-api:8000"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def main() -> None:
    value = json.loads(sys.stdin.buffer.read(4097))
    run_id = str(uuid.UUID(value["run_id"]))
    action = value["action"]
    cases = {
        "normal": {"title": "实验任务"},
        "missing": {},
        "empty": {"title": ""},
        "whitespace": {"title": "   "},
    }
    if action not in {"open", "observe", "close", *cases}:
        raise ValueError("未知实验动作。")
    path = f"/internal/labs/runs/{run_id}/"
    if action in cases:
        path += f"cases/{action}/"
    elif action == "close":
        path += "close/"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirect(),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    headers = {"Host": "127.0.0.1:5174", "Accept": "application/json"}
    data = None
    if action != "observe":
        with opener.open(
            urllib.request.Request(TARGET + "/api/v1/csrf/", headers=headers), timeout=2
        ) as response:
            csrf = json.loads(response.read(4097))["csrf_token"]
        headers.update(
            {
                "Origin": ORIGIN,
                "X-CSRFToken": csrf,
                "Content-Type": "application/json",
                "Idempotency-Key": run_id,
            }
        )
        data = json.dumps(cases.get(action, {})).encode()
    request = urllib.request.Request(TARGET + path, data=data, headers=headers)
    try:
        response = opener.open(request, timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = response.read(16385)
        if (
            len(payload) > 16384
            or response.headers.get_content_type() != "application/json"
        ):
            raise ValueError("示例返回超限或非 JSON 响应。")
        print(json.dumps({"status": response.status, "body": json.loads(payload)}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError):
        # 原始网络错误可能含环境信息，不转发 stderr 或响应正文。
        sys.exit(2)
