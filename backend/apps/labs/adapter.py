import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

VERSION = "task-board/1.0.0+request-validation/1"


class LabFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def exchange(run_id: uuid.UUID, action: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(Path(__file__).with_name("transport_worker.py")),
            ],
            input=json.dumps({"run_id": str(run_id), "action": action}).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=6,
            check=False,
            env={
                key: value
                for key, value in os.environ.items()
                if key in {"SYSTEMROOT", "WINDIR", "PATH"}
            },
        )
    except subprocess.TimeoutExpired:
        raise LabFailure("LAB_TIMEOUT") from None
    except OSError:
        raise LabFailure("LAB_UNAVAILABLE") from None
    if result.returncode or len(result.stdout) > 32768:
        raise LabFailure("LAB_UNAVAILABLE")
    try:
        value = json.loads(result.stdout)
        if (
            not isinstance(value, dict)
            or set(value) != {"status", "body"}
            or type(value["status"]) is not int
            or not isinstance(value["body"], dict)
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise LabFailure("LAB_INVALID_RESPONSE") from None
    return value


def observe(run_id: uuid.UUID, action: str) -> dict[str, Any]:
    response = exchange(run_id, action)
    body: dict[str, Any] = response["body"]
    if (
        response["status"] != 200
        or set(body)
        != {
            "id",
            "example_version",
            "closed",
            "record_count",
            "deleted_count",
            "expires_at",
        }
        or body["id"] != str(run_id)
        or body["example_version"] != VERSION
        or type(body["closed"]) is not bool
        or any(
            type(body[key]) is not int or not 0 <= body[key] <= 4
            for key in ("record_count", "deleted_count")
        )
        or not isinstance(body["expires_at"], str)
    ):
        raise LabFailure("LAB_INVALID_RESPONSE")
    if action == "close" and (not body["closed"] or body["record_count"] != 0):
        raise LabFailure("LAB_CLEANUP_FAILED")
    return body


def validate_case(response: dict[str, Any], case: str) -> None:
    body, status = response["body"], response["status"]
    if case == "normal":
        try:
            valid = (
                status in {200, 201}
                and set(body) == {"id", "title", "created_at"}
                and str(uuid.UUID(body["id"])) == body["id"]
                and body["title"] == "实验任务"
                and isinstance(body["created_at"], str)
            )
        except (KeyError, ValueError, TypeError, AttributeError):
            valid = False
    else:
        valid = (
            status == 400
            and set(body) == {"code", "message", "details", "request_id"}
            and body["code"] == "VALIDATION_ERROR"
            and isinstance(body["details"], dict)
            and all(isinstance(body[key], str) for key in ("message", "request_id"))
        )
    if not valid:
        raise LabFailure("LAB_INVALID_RESPONSE")
