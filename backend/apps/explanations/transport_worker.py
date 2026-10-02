"""固定 HTTP 子进程；仅处理父进程给定的请求，不加载导入源码。"""

import http.client
import json
import sys
import urllib.error
import urllib.request
from typing import Any


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def request_once(payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        payload["url"],
        data=json.dumps(payload["body"], ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + payload["key"],
            "Accept": "application/json",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=None) as response:
            if response.status != 200:
                return {"error": "MODEL_SERVICE_ERROR"}
            data = response.read()
            try:
                return {"response": json.loads(data)}
            except (ValueError, UnicodeError, RecursionError):
                return {"error": "MODEL_INVALID_RESPONSE"}
    except urllib.error.HTTPError as exc:
        code = (
            "MODEL_AUTH_FAILED"
            if exc.code in {401, 403}
            else "MODEL_RATE_LIMITED"
            if exc.code == 429
            else "MODEL_SERVICE_ERROR"
        )
        exc.close()
        return {"error": code}
    except TimeoutError:
        return {"error": "MODEL_TIMEOUT"}
    except (urllib.error.URLError, OSError, http.client.HTTPException):
        return {"error": "MODEL_CONNECTION_FAILED"}


if __name__ == "__main__":
    try:
        incoming = sys.stdin.buffer.read()
        result = request_once(json.loads(incoming))
    except Exception:
        # 子进程最终边界不输出异常文本，防止凭据、正文或宿主信息泄漏。
        result = {"error": "MODEL_INVALID_RESPONSE"}
    sys.stdout.buffer.write(
        json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    )
