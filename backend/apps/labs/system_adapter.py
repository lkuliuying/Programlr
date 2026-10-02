"""只启动可信固定程序；超时明确终止和等待，不继承工作台秘密。"""

import ipaddress
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROGRAM = Path(__file__).resolve().parents[3] / "examples/system-labs/probe.py"
MAX_OUTPUT = 4096


class SystemLabFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def stop_and_reap(process: subprocess.Popen[bytes]) -> bytes:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            # 固定程序不创建后代；组终止失败时仍尝试终止这个直接子进程。
            process.kill()
    output, _ = process.communicate(timeout=2)
    return output


def execute_case(lab_id: str, case: str) -> dict[str, Any]:
    if lab_id not in {"container-network", "subprocess-lifecycle"} or case not in {
        "first",
        "second",
    }:
        raise SystemLabFailure("SYSTEM_LAB_INVALID_INPUT")
    if sys.platform != "linux":
        raise SystemLabFailure("SYSTEM_LAB_PLATFORM_UNSUPPORTED")
    started = time.monotonic()
    network = lab_id == "container-network"
    mode = ("network-" if network else "process-") + case
    result: dict[str, Any] = {
        "case_id": case,
        "status": "observed",
        "hostname": None,
        "addresses": [],
        "connected": None,
        "pid": None,
        "return_code": None,
        "stdout": "",
        "timed_out": False,
        "reaped": None,
        "error_code": None,
    }
    process: subprocess.Popen[bytes] | None = None
    output = b""
    try:
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(PROGRAM), mode, str(os.getpid())],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={},
            start_new_session=True,
        )
        result["pid"] = process.pid
        try:
            output, _ = process.communicate(
                timeout=6 if network else 2 if case == "first" else 0.5
            )
        except subprocess.TimeoutExpired as exc:
            result["timed_out"] = True
            output = exc.output or b""
            output = stop_and_reap(process)
        result["return_code"] = process.returncode
        result["reaped"] = process.returncode is not None
        if len(output) > MAX_OUTPUT:
            raise SystemLabFailure("SYSTEM_LAB_INVALID_RESPONSE")
        decoded = output.decode("utf-8")
        if network:
            if result["timed_out"]:
                result.update(
                    status="unavailable",
                    hostname="localhost" if case == "first" else "task-board-api",
                    connected=False,
                    error_code="PROBE_TIMEOUT",
                )
            elif process.returncode != 0:
                raise SystemLabFailure("SYSTEM_LAB_INVALID_RESPONSE")
            else:
                value = json.loads(decoded)
                validate_network(value, case)
                result.update(value)
        else:
            result["stdout"] = decoded
            if (
                case == "first"
                and (
                    result["timed_out"]
                    or process.returncode != 0
                    or decoded != "ready\ncompleted\n"
                )
            ) or (
                case == "second"
                and (not result["timed_out"] or process.returncode != -signal.SIGKILL)
            ):
                raise SystemLabFailure("SYSTEM_LAB_INVALID_RESPONSE")
    except (OSError, subprocess.TimeoutExpired):
        result.update(status="unavailable", error_code="SYSTEM_LAB_UNAVAILABLE")
    except (ValueError, UnicodeError, SystemLabFailure):
        result.update(status="invalid", error_code="SYSTEM_LAB_INVALID_RESPONSE")
    finally:
        if process is not None:
            if process.returncode is None:
                try:
                    output = stop_and_reap(process)
                    result["return_code"] = process.returncode
                    result["reaped"] = process.returncode is not None
                except (OSError, subprocess.TimeoutExpired):
                    result.update(
                        status="unavailable",
                        reaped=False,
                        error_code="SYSTEM_LAB_CLEANUP_FAILED",
                    )
            if process.stdout is not None:
                process.stdout.close()
    result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result


def validate_network(value: Any, case: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "hostname",
        "addresses",
        "connected",
        "error_code",
    }:
        raise ValueError("固定网络观测结构无效。")
    if (
        value["hostname"] != ("localhost" if case == "first" else "task-board-api")
        or type(value["connected"]) is not bool
        or not isinstance(value["addresses"], list)
        or len(value["addresses"]) > 8
    ):
        raise ValueError("固定网络观测目标无效。")
    for address in value["addresses"]:
        if not isinstance(address, str):
            raise ValueError("地址格式无效。")
        ipaddress.ip_address(address)
    if len(set(value["addresses"])) != len(value["addresses"]):
        raise ValueError("地址重复。")
    if value["connected"]:
        if not value["addresses"] or value["error_code"] is not None:
            raise ValueError("连接观测缺少解析依据。")
    elif value["error_code"] not in {
        "DNS_FAILED",
        "CONNECT_REFUSED",
        "CONNECT_TIMEOUT",
        "CONNECT_FAILED",
    }:
        raise ValueError("连接失败类别无效。")
