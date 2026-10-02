import json
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.explanations.adapter import ModelFailure, complete, decode_completion
from apps.explanations.configuration import ModelConfiguration, configuration
from apps.explanations.transport_worker import request_once
from apps.explanations.validation import SECTIONS, validate_content
from common.errors import ApiProblem

OPTIONS = {
    "base_url": "https://model-test.invalid/v1",
    "model": "test-model",
}
REF = {
    "snapshot_id": "00000000-0000-0000-0000-000000000001",
    "file_path": "views.py",
    "start_line": 2,
    "end_line": 5,
}
SNIPPETS = [{"source_ref": REF, "content": "受控示例", "sha256": "a" * 64}]


def valid_content(ref: dict[str, Any] | None = None) -> str:
    return json.dumps(
        {
            section: [
                {
                    "kind": "source_fact"
                    if section != "knowledge"
                    else "general_principle",
                    "text": "代码声明了输入约束。",
                    "source_refs": [ref or REF] if section != "knowledge" else [],
                }
            ]
            for section in SECTIONS
        }
    )


def completion() -> dict[str, Any]:
    return {
        "model": "test-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": valid_content()},
            }
        ],
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"base_url": "http://model-test.invalid/v1"},
        {"base_url": "https://user@model-test.invalid"},
        {"base_url": "https://model-test.invalid/?x=1"},
        {"base_url": "https://model-test.invalid/#x"},
        {"base_url": "https://model-test.invalid:0"},
        {"model": "bad\nmodel"},
    ],
)
def test_invalid_configuration(changes: dict[str, str]) -> None:
    with (
        override_settings(MODEL_OPTIONS={**OPTIONS, **changes}),
        pytest.raises(ApiProblem) as failure,
    ):
        configuration()
    assert failure.value.machine_code == "MODEL_CONFIGURATION_INVALID"


@pytest.mark.parametrize("options", [{}, {"base_url": OPTIONS["base_url"]}])
def test_unconfigured_model_does_not_require_credentials(
    options: dict[str, str],
) -> None:
    with (
        override_settings(MODEL_OPTIONS=options),
        pytest.raises(ApiProblem) as failure,
    ):
        configuration()
    assert failure.value.machine_code == "MODEL_NOT_CONFIGURED"


def test_configuration_only_binds_target_and_model() -> None:
    with override_settings(
        MODEL_OPTIONS={
            **OPTIONS,
            "enabled": "false",
            "timeout": "1",
            "context_bytes": "1",
            "output_tokens": "1",
            "token_field": "unknown",
        }
    ):
        assert configuration().binding() == OPTIONS


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ("empty", "MODEL_EMPTY_RESPONSE"),
        ("refusal", "MODEL_REFUSED"),
        ("length", "MODEL_TRUNCATED"),
        ("tools", "MODEL_INVALID_RESPONSE"),
        ("usage", "MODEL_INVALID_RESPONSE"),
    ],
)
def test_output_errors(change: str, code: str) -> None:
    value = completion()
    message = value["choices"][0]["message"]
    if change == "empty":
        message["content"] = " "
    elif change == "refusal":
        message["refusal"] = "无法处理"
    elif change == "length":
        value["choices"][0]["finish_reason"] = "length"
    elif change == "tools":
        message["tool_calls"] = [{"id": "unexpected"}]
    else:
        value["usage"] = {"total_tokens": True}
    with pytest.raises(ModelFailure) as failure:
        decode_completion(value)
    assert failure.value.code == code


def test_usage_unknown_and_valid_content() -> None:
    assert decode_completion(completion())[2] is None
    assert set(validate_content(valid_content(), SNIPPETS)) == set(SECTIONS)


@pytest.mark.parametrize(
    "ref",
    [
        {**REF, "snapshot_id": "00000000-0000-0000-0000-000000000002"},
        {**REF, "file_path": "missing.py"},
        {**REF, "start_line": 1},
        {**REF, "end_line": 6},
        {**REF, "start_line": True},
    ],
)
def test_unpreviewed_reference_rejected(ref: dict[str, Any]) -> None:
    with pytest.raises(ModelFailure):
        validate_content(valid_content(ref), SNIPPETS)


@pytest.mark.parametrize(
    "value",
    [
        "<script>alert(1)</script>",
        "javascript:run()",
        "https://evil.invalid",
        "data:text/html,foo",
        "x\u0000y",
    ],
)
def test_unsafe_content_rejected(value: str) -> None:
    content = json.loads(valid_content())
    content["purpose"][0]["text"] = value
    with pytest.raises(ModelFailure) as failure:
        validate_content(json.dumps(content), SNIPPETS)
    assert failure.value.code == "MODEL_UNSAFE_CONTENT"


def test_missing_evidence_and_unknown_fields_rejected() -> None:
    content = json.loads(valid_content())
    content["purpose"][0]["source_refs"] = []
    with pytest.raises(ModelFailure):
        validate_content(json.dumps(content), SNIPPETS)
    content["tool_calls"] = []
    with pytest.raises(ModelFailure):
        validate_content(json.dumps(content), SNIPPETS)


@pytest.fixture
def server() -> Any:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            state["calls"] += 1
            state["body"] = json.loads(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            if state["mode"] == "disconnect":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if state["mode"] == "slow":
                time.sleep(2)
            status = state.get("status", 200)
            self.send_response(status)
            if status == 302:
                self.send_header("Location", state["url"])
            self.end_headers()
            response = state.get("response", completion())
            if state["mode"] == "large":
                response["choices"][0]["message"]["reasoning_content"] = "x" * 300_000
            data = (
                b"invalid"
                if state["mode"] == "invalid"
                else json.dumps(response).encode()
            )
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    state: dict[str, Any] = {"calls": 0, "mode": "normal"}
    instance = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state["url"] = f"http://127.0.0.1:{instance.server_port}/v1/chat/completions"
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(3)


@pytest.mark.parametrize(
    ("status", "mode", "expected"),
    [
        (200, "normal", None),
        (401, "normal", "MODEL_AUTH_FAILED"),
        (429, "normal", "MODEL_RATE_LIMITED"),
        (302, "normal", "MODEL_SERVICE_ERROR"),
        (200, "large", None),
        (200, "invalid", "MODEL_INVALID_RESPONSE"),
        (200, "disconnect", "MODEL_CONNECTION_FAILED"),
    ],
)
def test_local_http_is_single_attempt(
    server: dict[str, Any], status: int, mode: str, expected: str | None
) -> None:
    server.update(status=status, mode=mode)
    result = request_once(
        {
            "url": server["url"],
            "key": "synthetic-test-only",
            "body": {"stream": False},
        }
    )
    assert result.get("error") == expected and server["calls"] == 1


def test_subprocess_has_no_request_limits_and_renews_claim(
    server: dict[str, Any],
) -> None:
    config = ModelConfiguration(
        server["url"].removesuffix("/chat/completions"),
        "test-model",
    )
    server["mode"] = "slow"
    messages = [{"role": "user", "content": "x" * 150_000}]
    with patch(
        "apps.explanations.adapter.credential", return_value="synthetic-test-only"
    ):
        renewals: list[float] = []

        def renew() -> bool:
            renewals.append(time.monotonic())
            return True

        started = time.monotonic()
        assert (
            complete(config, messages, renew_claim=renew, poll_interval=0.1)[1]
            == "test-model"
        )
    assert time.monotonic() - started >= 2 and len(renewals) > 1
    assert server["body"] == {
        "model": "test-model",
        "messages": messages,
        "stream": False,
    }
    assert server["calls"] == 1


@pytest.mark.parametrize("tokens", [0, 4095, 4096, 4097, 14623, 100_000_001])
def test_reported_usage_is_saved_without_output_budget(
    server: dict[str, Any], tokens: int
) -> None:
    response = completion()
    response["usage"] = {
        "prompt_tokens": 6464,
        "completion_tokens": tokens,
        "total_tokens": 6464 + tokens,
        "completion_tokens_details": {"reasoning_tokens": max(0, tokens - 1)},
    }
    server["response"] = response
    config = ModelConfiguration(
        server["url"].removesuffix("/chat/completions"),
        "test-model",
    )
    with patch(
        "apps.explanations.adapter.credential", return_value="synthetic-test-only"
    ):
        usage = complete(config, [])[2]
        assert usage is not None and usage["completion_tokens"] == tokens
    assert server["calls"] == 1
    assert set(server["body"]) == {"model", "messages", "stream"}


@pytest.mark.parametrize("tokens", [True, -1, "4097"])
def test_invalid_usage_is_still_rejected(tokens: object) -> None:
    response = completion()
    response["usage"] = {
        "prompt_tokens": 6464,
        "completion_tokens": tokens,
        "total_tokens": 6465,
    }
    config = ModelConfiguration("https://model-test.invalid/v1", "test-model")
    with (
        patch(
            "apps.explanations.adapter.credential", return_value="synthetic-test-only"
        ),
        patch("apps.explanations.adapter.subprocess.Popen") as transport,
        pytest.raises(ModelFailure) as failure,
    ):
        process = transport.return_value.__enter__.return_value
        process.returncode = 0
        process.communicate.return_value = (
            json.dumps({"response": response}).encode(),
            b"",
        )
        complete(config, [])
    assert failure.value.code == "MODEL_INVALID_RESPONSE"
    transport.assert_called_once()


@pytest.mark.parametrize("mode", ["lost", "database_failure"])
def test_lost_lease_or_renewal_failure_stops_transport(mode: str) -> None:
    config = ModelConfiguration("https://model-test.invalid/v1", "test-model")
    with (
        patch(
            "apps.explanations.adapter.credential", return_value="synthetic-test-only"
        ),
        patch("apps.explanations.adapter.subprocess.Popen") as transport,
        patch("apps.explanations.adapter.decode_completion") as decode,
    ):
        process = transport.return_value.__enter__.return_value
        process.poll.return_value = None
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("fixed-worker", 0.1),
            (b"", b""),
        ]

        def renew() -> bool:
            if mode == "database_failure":
                raise RuntimeError("合成续期失败")
            return False

        with pytest.raises(ModelFailure if mode == "lost" else RuntimeError):
            complete(config, [], renew_claim=renew, poll_interval=0.1)
    process.kill.assert_called_once()
    transport.assert_called_once()
    decode.assert_not_called()
