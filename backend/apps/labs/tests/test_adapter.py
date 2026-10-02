import subprocess
import uuid
from unittest.mock import patch

import pytest

from apps.labs.adapter import LabFailure, exchange, observe


@pytest.mark.parametrize(
    "result",
    [b"not-json", b"[]", b'{"status":true,"body":{}}', b"x" * 32769],
    ids=["non-json", "array", "boolean-status", "oversize"],
)
def test_invalid_transport(result: bytes) -> None:
    with patch(
        "subprocess.run", return_value=subprocess.CompletedProcess([], 0, result)
    ):
        with pytest.raises(LabFailure):
            exchange(uuid.uuid4(), "observe")


def test_timeout_and_no_automatic_retry() -> None:
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired([], 6)) as call:
        with pytest.raises(LabFailure, match="LAB_TIMEOUT"):
            exchange(uuid.uuid4(), "normal")
        assert call.call_count == 1


def test_cross_run_and_cleanup_not_confirmed() -> None:
    run = uuid.uuid4()
    for body in (
        {},
        {
            "id": str(uuid.uuid4()),
            "example_version": "task-board/1.0.0+request-validation/1",
            "closed": False,
            "record_count": 1,
            "deleted_count": 0,
            "expires_at": "2026-09-29T00:00:00Z",
        },
    ):
        with patch(
            "apps.labs.adapter.exchange", return_value={"status": 200, "body": body}
        ):
            with pytest.raises(LabFailure):
                observe(run, "close")
