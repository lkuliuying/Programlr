"""仅供固定系统实验使用的可信程序，不接收命令、地址或资源参数。"""

import ctypes
import json
import os
import resource
import signal
import socket
import sys
import time
from typing import Any

MODES = {"network-first", "network-second", "process-first", "process-second"}


def restrict(parent: int) -> None:
    if sys.platform != "linux" or parent <= 1:
        raise ValueError("固定实验需要 Linux 父进程。")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError("无法设置父进程退出保护。")
    if os.getppid() != parent:
        raise OSError("父进程已变化，拒绝继续运行。")
    resource.setrlimit(resource.RLIMIT_CPU, (1, 2))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))


def network(mode: str) -> dict[str, Any]:
    hostname = "localhost" if mode == "network-first" else "task-board-api"
    try:
        records = socket.getaddrinfo(hostname, 8000, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return {
            "hostname": hostname,
            "addresses": [],
            "connected": False,
            "error_code": "DNS_FAILED",
        }
    addresses: list[str] = []
    error = "CONNECT_FAILED"
    connected = False
    for family, kind, protocol, _, address in records[:8]:
        host = str(address[0])
        if host not in addresses:
            addresses.append(host)
        try:
            with socket.socket(family, kind, protocol) as connection:
                connection.settimeout(0.4)
                connection.connect(address)
            connected = True
        except TimeoutError:
            error = "CONNECT_TIMEOUT"
        except ConnectionRefusedError:
            error = "CONNECT_REFUSED"
        except OSError:
            error = "CONNECT_FAILED"
    return {
        "hostname": hostname,
        "addresses": addresses,
        "connected": connected,
        "error_code": None if connected else error,
    }


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in MODES:
        return 2
    try:
        restrict(int(sys.argv[2]))
    except (ValueError, OSError):
        return 2
    mode = sys.argv[1]
    if mode.startswith("network-"):
        print(
            json.dumps(network(mode), ensure_ascii=False, separators=(",", ":")),
            flush=True,
        )
    else:
        print("ready", flush=True)
        if mode == "process-second":
            time.sleep(5)
        print("completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
