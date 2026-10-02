import io
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.labs.system_adapter import (
    PROGRAM,
    SystemLabFailure,
    execute_case,
    validate_network,
)


@pytest.mark.skipif(
    sys.platform != "linux", reason="真实进程与命名空间验收使用 Linux 容器。"
)
def test_real_process_output_timeout_and_wait_reaps() -> None:
    normal = execute_case("subprocess-lifecycle", "first")
    assert (
        normal["status"] == "observed"
        and normal["pid"] > 1
        and normal["return_code"] == 0
    )
    assert (
        normal["stdout"] == "ready\ncompleted\n"
        and normal["reaped"]
        and not normal["timed_out"]
    )
    timeout = execute_case("subprocess-lifecycle", "second")
    assert (
        timeout["status"] == "observed" and timeout["timed_out"] and timeout["reaped"]
    )
    assert timeout["return_code"] == -signal.SIGKILL and timeout["stdout"] == "ready\n"
    for result in (normal, timeout):
        with pytest.raises(ChildProcessError):
            os.waitpid(result["pid"], os.WNOHANG)


@pytest.mark.skipif(
    sys.platform != "linux", reason="真实资源上限与父进程退出保护使用 Linux。"
)
def test_real_resource_limits_and_parent_death_signal() -> None:
    child = subprocess.Popen(
        [sys.executable, "-I", "-B", str(PROGRAM), "process-second", str(os.getpid())],
        stdout=subprocess.PIPE,
        env={},
    )
    try:
        assert child.stdout is not None and child.stdout.readline() == b"ready\n"
        limits = Path(f"/proc/{child.pid}/limits").read_text()
        assert "134217728" in next(
            line for line in limits.splitlines() if line.startswith("Max address space")
        )
        assert "32" in next(
            line for line in limits.splitlines() if line.startswith("Max open files")
        )
        assert next(
            line for line in limits.splitlines() if line.startswith("Max cpu time")
        ).split()[-3:] == ["1", "2", "seconds"]
    finally:
        child.kill()
        child.communicate(timeout=2)
    helper = "import subprocess,sys,os,json; p=subprocess.Popen([sys.executable,'-I','-B',sys.argv[1],'process-second',str(os.getpid())],stdout=subprocess.PIPE,env={}); ready=p.stdout.readline(); print(json.dumps({'pid':p.pid,'ready':ready.decode()}),flush=True); os._exit(0)"
    parent = subprocess.run(
        [sys.executable, "-I", "-c", helper, str(PROGRAM)],
        capture_output=True,
        timeout=4,
        check=True,
    )
    result = json.loads(parent.stdout)
    assert result["ready"] == "ready\n"
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and Path(f"/proc/{result['pid']}").exists():
        time.sleep(0.02)
    assert not Path(f"/proc/{result['pid']}").exists()


@pytest.mark.parametrize(
    "value",
    [
        None,
        {},
        {
            "hostname": "external",
            "addresses": [],
            "connected": True,
            "error_code": None,
        },
        {
            "hostname": "localhost",
            "addresses": ["invalid"],
            "connected": False,
            "error_code": "DNS_FAILED",
        },
        {
            "hostname": "localhost",
            "addresses": [],
            "connected": True,
            "error_code": None,
        },
    ],
)
def test_invalid_network_response(value: object) -> None:
    with pytest.raises(ValueError):
        validate_network(value, "first")


def test_platform_and_arbitrary_action_refused() -> None:
    with (
        patch("apps.labs.system_adapter.sys.platform", "win32"),
        pytest.raises(SystemLabFailure) as failure,
    ):
        execute_case("subprocess-lifecycle", "first")
    assert failure.value.code == "SYSTEM_LAB_PLATFORM_UNSUPPORTED"
    with pytest.raises(SystemLabFailure):
        execute_case("arbitrary", "command")


def test_spawn_failure_and_cleanup_failure_are_explicit() -> None:
    with (
        patch("apps.labs.system_adapter.sys.platform", "linux"),
        patch("apps.labs.system_adapter.subprocess.Popen", side_effect=OSError),
    ):
        result = execute_case("subprocess-lifecycle", "first")
    assert result["status"] == "unavailable" and result["pid"] is None
    process = subprocess.Popen
    from unittest.mock import MagicMock

    fake = MagicMock(spec=process)
    fake.pid, fake.returncode, fake.stdout = 100, None, io.BytesIO()
    fake.communicate.side_effect = subprocess.TimeoutExpired("fixed", 1)
    with (
        patch("apps.labs.system_adapter.sys.platform", "linux"),
        patch("apps.labs.system_adapter.subprocess.Popen", return_value=fake),
        patch("apps.labs.system_adapter.stop_and_reap", side_effect=PermissionError),
    ):
        result = execute_case("subprocess-lifecycle", "second")
    assert (
        result["reaped"] is False
        and result["error_code"] == "SYSTEM_LAB_CLEANUP_FAILED"
    )
    assert fake.stdout.closed
