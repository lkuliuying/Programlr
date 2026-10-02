import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.explanations.configuration import ModelConfiguration, credential, encode


class ModelFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__("模型请求未能生成有效讲解。")


def decode_completion(value: Any) -> tuple[str, str, dict[str, int] | None]:
    try:
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("choices"), list)
            or len(value["choices"]) != 1
        ):
            raise ValueError
        choice = value["choices"][0]
        message = choice["message"]
        if message.get("refusal") or choice.get("finish_reason") == "content_filter":
            raise ModelFailure("MODEL_REFUSED")
        if choice.get("finish_reason") == "length":
            raise ModelFailure("MODEL_TRUNCATED")
        if (
            choice.get("finish_reason") != "stop"
            or message.get("role") != "assistant"
            or message.get("tool_calls")
            or message.get("function_call")
        ):
            raise ValueError
        content, model = message.get("content"), value.get("model")
        if not isinstance(content, str) or not content.strip():
            raise ModelFailure("MODEL_EMPTY_RESPONSE")
        if (
            not isinstance(model, str)
            or not 1 <= len(model) <= 200
            or any(ord(c) < 32 for c in model)
        ):
            raise ValueError
        usage = value.get("usage")
        if usage is not None:
            keys = ("prompt_tokens", "completion_tokens", "total_tokens")
            if not isinstance(usage, dict) or any(
                type(usage.get(k)) is not int or usage[k] < 0 for k in keys
            ):
                raise ValueError
            usage = {k: usage[k] for k in keys}
        return content, model, usage
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ModelFailure("MODEL_INVALID_RESPONSE") from None


def complete(
    config: ModelConfiguration,
    messages: list[dict[str, str]],
    *,
    renew_claim: Callable[[], bool] | None = None,
    poll_interval: float = 5,
) -> tuple[str, str, dict[str, int] | None]:
    payload = encode(
        {
            "url": config.base_url + "/chat/completions",
            "key": credential(),
            "body": {
                "model": config.model,
                "messages": messages,
                "stream": False,
            },
        }
    )
    environment = {"PATH": str(Path(sys.executable).parent), "LANG": "C.UTF-8"}
    if os.name == "nt" and "SYSTEMROOT" in os.environ:
        environment["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    script = Path(__file__).with_name("transport_worker.py")
    try:
        # stdin 传递凭据；轮询仅用于领取续期，不限制请求总时长或重发请求。
        with subprocess.Popen(
            [sys.executable, "-I", str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=script.parent,
            env=environment,
        ) as process:
            try:
                pending: bytes | None = payload
                while True:
                    try:
                        output, _ = process.communicate(
                            pending, timeout=poll_interval if renew_claim else None
                        )
                        break
                    except subprocess.TimeoutExpired:
                        pending = None
                        if renew_claim is None or not renew_claim():
                            raise ModelFailure("EXECUTION_INTERRUPTED") from None
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        if process.returncode:
            raise ModelFailure("MODEL_INVALID_RESPONSE")
        result = json.loads(output)
        if "error" in result:
            allowed = {
                "MODEL_SERVICE_ERROR",
                "MODEL_AUTH_FAILED",
                "MODEL_RATE_LIMITED",
                "MODEL_INVALID_RESPONSE",
                "MODEL_TIMEOUT",
                "MODEL_CONNECTION_FAILED",
            }
            raise ModelFailure(
                result["error"]
                if result["error"] in allowed
                else "MODEL_INVALID_RESPONSE"
            )
        return decode_completion(result["response"])
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        raise ModelFailure("MODEL_CONNECTION_FAILED") from None
