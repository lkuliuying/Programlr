"""管理 v1.0 独立演示验收、规模评估和自身资源；不读取真实环境配置。"""

import argparse
import contextlib
import importlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import traceback
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from v1_acceptance import (
    MEMORY_COMMAND,
    Client,
    benchmark,
    learning_checks,
    read_memory_metrics,
)
from v1_acceptance import ORIGIN as ORIGIN

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / ".runtime/v1-verify"
STATE = DIRECTORY / "state.json"
REPORT = DIRECTORY / "report.json"
PROJECT_PATTERN = re.compile(r"learning-lab-v1-verify-[a-f0-9]{12}\Z")
SERVICES = (
    "api",
    "worker",
    "reconciler",
    "frontend",
    "task-board-api",
    "lab-reconciler",
)


def save_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def validate_state(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("version") != 1
        or not isinstance(value.get("project"), str)
        or not PROJECT_PATTERN.fullmatch(value["project"])
        or value.get("origin") != ORIGIN
        or value.get("status") not in {"starting", "ready", "failed", "stopped"}
    ):
        raise RuntimeError("验收状态无效，拒绝操作 Docker 资源。")
    return value


def load_state() -> dict[str, Any]:
    try:
        return validate_state(json.loads(STATE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        raise RuntimeError("验收状态不可读，请核对本次状态文件。") from None


class Docker:
    def __init__(self, executable: str) -> None:
        self.executable = executable
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("COMPOSE_", "MODEL_"))
            and key not in {"DOCKER_HOST", "DOCKER_CONTEXT"}
        }

    def call(self, *values: str, timeout: int = 90) -> str:
        try:
            result = subprocess.run(
                [self.executable, *values],
                env=self.environment,
                encoding="utf-8",
                text=True,
                capture_output=True,
                timeout=timeout,
                check=True,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            # Docker 错误可能含环境配置，不向终端复制原始输出。
            raise RuntimeError(
                "Docker 命令未通过；请核对服务及本次验收状态。"
            ) from None

    def local_context(self) -> None:
        endpoint = self.call(
            "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"
        )
        if not endpoint.startswith(("npipe://", "unix://")):
            raise RuntimeError("只允许本机 Docker socket，拒绝远程上下文。")

    def compose(self, project: str, *values: str, timeout: int = 90) -> str:
        if not PROJECT_PATTERN.fullmatch(project):
            raise RuntimeError("项目名称不属于本次验收。")
        if (DIRECTORY / "empty.env").stat().st_size:
            raise RuntimeError("验收环境文件非空，拒绝加载配置。")
        return self.call(
            "compose",
            "--env-file",
            str(DIRECTORY / "empty.env"),
            "-p",
            project,
            "-f",
            str(ROOT / "compose.yaml"),
            "-f",
            str(ROOT / "infra/docker/compose.m5-verify.yaml"),
            "-f",
            str(ROOT / "infra/docker/compose.v1-verify.yaml"),
            "--profile",
            "task-board",
            *values,
            timeout=timeout,
        )

    def resources(self, project: str) -> dict[str, list[str]]:
        if not PROJECT_PATTERN.fullmatch(project):
            raise RuntimeError("项目名称不属于本次验收。")
        result = {}
        for kind in ("container", "network", "volume"):
            values = ("ps", "-aq") if kind == "container" else (kind, "ls", "-q")
            ids = self.call(
                *values, "--filter", "label=com.docker.compose.project=" + project
            ).splitlines()
            for identity in ids:
                labels = self.call(
                    kind,
                    "inspect",
                    "--format",
                    "{{json .Config.Labels}}"
                    if kind == "container"
                    else "{{json .Labels}}",
                    identity,
                )
                parsed = json.loads(labels)
                if (
                    not isinstance(parsed, dict)
                    or parsed.get("com.docker.compose.project") != project
                ):
                    raise RuntimeError("资源归属不一致，拒绝清理或验收。")
                if kind == "container" and (
                    not parsed.get("com.docker.compose.config-hash")
                    or not str(
                        parsed.get("com.docker.compose.container-number", "")
                    ).isdecimal()
                ):
                    raise RuntimeError("存在仅继承镜像项目标签的容器，拒绝接管或清理。")
            result[kind] = ids
        return result

    def service(self, project: str, service: str) -> str:
        values = self.call(
            "ps",
            "-q",
            "--filter",
            "label=com.docker.compose.project=" + project,
            "--filter",
            "label=com.docker.compose.service=" + service,
            "--filter",
            "label=com.docker.compose.config-hash",
        ).splitlines()
        if len(values) != 1:
            raise RuntimeError(f"验收服务 {service} 缺失或归属不唯一。")
        return values[0]


def stop(docker: Docker, state: dict[str, Any], *, remove_data: bool = False) -> None:
    validate_state(state)
    docker.resources(state["project"])
    docker.compose(
        state["project"],
        "down",
        "--remove-orphans",
        *(["--volumes"] if remove_data else []),
        timeout=120,
    )
    remaining = docker.resources(state["project"])
    if (
        remaining["container"]
        or remaining["network"]
        or (remove_data and remaining["volume"])
    ):
        raise RuntimeError("本次资源清理未确认，状态文件已保留。")
    state["status"] = "stopped"
    state["test_data_retained"] = bool(remaining["volume"])
    save_json(STATE, state)
    print(
        "本次验收栈已关闭；" + ("测试卷已删除。" if remove_data else "默认保留测试卷。")
    )


def start(docker: Docker, *, build: bool = False) -> dict[str, Any]:
    if STATE.exists():
        previous = load_state()
        if previous["status"] != "stopped":
            raise RuntimeError("已有验收状态，请先查询或关闭原验收栈。")
        save_json(DIRECTORY / (previous["project"] + ".json"), previous)
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", 5181))
        except OSError:
            raise RuntimeError("5181 端口不可用，未创建验收资源。") from None
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    environment_file = DIRECTORY / "empty.env"
    if environment_file.exists() and environment_file.stat().st_size:
        raise RuntimeError("验收环境文件非空，拒绝加载配置。")
    environment_file.touch(exist_ok=True)
    state: dict[str, Any] = {
        "version": 1,
        "project": "learning-lab-v1-verify-" + uuid.uuid4().hex[:12],
        "status": "starting",
        "origin": ORIGIN,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if any(docker.resources(state["project"]).values()):
        raise RuntimeError("随机验收项目存在资源冲突，未接管已有资源。")
    save_json(STATE, state)
    try:
        if build:
            print("按固定锁文件构建 v1.0 本地镜像。", flush=True)
            # 显式构建避免 Compose 将项目标签写入镜像，污染后来启动的独立容器归属。
            for dockerfile, image, context in (
                ("backend.Dockerfile", "learning-lab-backend:1.0.0", ROOT),
                ("frontend.Dockerfile", "learning-lab-frontend:1.0.0", ROOT),
                (
                    "task-board-backend.Dockerfile",
                    "learning-lab-task-board-backend:v1-verify",
                    ROOT / "examples/task-board/backend",
                ),
            ):
                docker.call(
                    "build",
                    "--pull=false",
                    "-f",
                    str(ROOT / "infra/docker" / dockerfile),
                    "-t",
                    image,
                    str(context),
                    timeout=900,
                )
        docker.compose(
            state["project"],
            "up",
            "-d",
            "--no-build",
            "--pull",
            "never",
            "--wait",
            "--wait-timeout",
            "120",
            *SERVICES,
            timeout=180,
        )
        client = Client()
        client.request("/api/v1/knowledge-curricula/")
        state["status"] = "ready"
        save_json(STATE, state)
    except (RuntimeError, OSError, ValueError):
        state["status"] = "failed"
        save_json(STATE, state)
        try:
            stop(docker, state)
        except RuntimeError:
            print(
                "启动失败且清理未确认，请用本入口 stop 核对；原状态保留。",
                file=sys.stderr,
            )
        raise RuntimeError("启动未完成，未宣称演示环境可用。") from None
    print("独立 v1.0 演示入口：" + ORIGIN)
    return state


@contextlib.contextmanager
def arguments(values: list[str]) -> Iterator[None]:
    previous = sys.argv
    sys.argv = values
    try:
        yield
    finally:
        sys.argv = previous


def checks(report: dict[str, Any]) -> None:
    m5 = importlib.import_module("check_m5_workspace")
    v02 = importlib.import_module("check_v02_workspace")
    v03 = importlib.import_module("check_v03_workspace")

    for module, name in ((v02, "v02-http"), (v03, "v03-http")):
        report["current_step"] = name
        save_json(REPORT, report)
        with arguments(
            [name, "--origin", ORIGIN, "--evidence", str(DIRECTORY / (name + ".json"))]
        ):
            module.main()
    old_origin, old_evidence = getattr(m5, "ORIGIN"), getattr(m5, "EVIDENCE")
    try:
        report["current_step"] = "request-validation-http"
        save_json(REPORT, report)
        source = json.loads((DIRECTORY / "v03-http.json").read_text(encoding="utf-8"))
        save_json(DIRECTORY / "m5-http.json", learning_checks(source))
        setattr(m5, "ORIGIN", ORIGIN)
        setattr(m5, "EVIDENCE", DIRECTORY / "m5-http.json")
        with arguments(["m5-http", "--labs-only"]):
            m5.main()
    finally:
        setattr(m5, "ORIGIN", old_origin)
        setattr(m5, "EVIDENCE", old_evidence)


def check(docker: Docker, state: dict[str, Any], *, repeats: int) -> None:
    validate_state(state)
    if state["status"] != "ready":
        raise RuntimeError("验收环境尚未就绪。")
    docker.resources(state["project"])
    for service in SERVICES:
        docker.service(state["project"], service)
    report: dict[str, Any] = {
        "version": "1.0.0",
        "status": "running",
        "project": state["project"],
        "started_at": datetime.now(UTC).isoformat(),
        "host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "logical_cpus": os.cpu_count(),
            "python": platform.python_version(),
        },
        "docker": docker.call(
            "info",
            "--format",
            "{{.OSType}} {{.Architecture}} {{.NCPU}} {{.MemTotal}} {{.ServerVersion}}",
        ),
        "real_user_trial": {"status": "not_performed", "participants": 0},
    }
    save_json(REPORT, report)
    try:
        started = time.monotonic()
        checks(report)
        report["http_workflow_seconds"] = round(time.monotonic() - started, 3)
        report["current_step"] = "benchmark"
        save_json(REPORT, report)
        report["benchmark"] = benchmark(repeats)
        report["current_step"] = "resources"
        resources = {}
        for service in ("api", "worker", "reconciler"):
            identity = docker.service(state["project"], service)
            resources[service] = read_memory_metrics(
                docker.call("exec", identity, "sh", "-c", MEMORY_COMMAND)
            )
            resources[service]["image_id"] = docker.call(
                "inspect", "--format", "{{.Image}}", identity
            )
            resources[service]["limits"] = docker.call(
                "inspect",
                "--format",
                "{{.HostConfig.NanoCpus}} {{.HostConfig.Memory}} {{.HostConfig.PidsLimit}}",
                identity,
            )
        report["resources"] = resources
        report["status"] = "passed"
        report["current_step"] = "completed"
        report["completed_at"] = datetime.now(UTC).isoformat()
    except (RuntimeError, OSError, ValueError, AssertionError, KeyError) as error:
        report["status"] = "failed"
        frames = traceback.extract_tb(error.__traceback__)
        report["failure"] = {
            "type": type(error).__name__,
            "location": f"{Path(frames[-1].filename).name}:{frames[-1].lineno}"
            if frames
            else None,
        }
        save_json(REPORT, report)
        raise RuntimeError(
            f"v1.0 的 {report['current_step']} 验收未通过，部分记录已保留；不自动重试。"
        ) from None
    save_json(REPORT, report)
    print("v1.0 工程主线与规模评估通过；报告：" + str(REPORT))
    print("真实用户试用尚未执行，工程验收不替代试用。")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "check", "stop"])
    parser.add_argument("--docker", default="docker")
    parser.add_argument(
        "--build", action="store_true", help="仅 start：按现有锁文件构建镜像"
    )
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=3)
    parser.add_argument(
        "--remove-test-data",
        action="store_true",
        help="仅 stop：删除本次归属已核对的测试卷",
    )
    args = parser.parse_args()
    if (args.build and args.action != "start") or (
        args.remove_test_data and args.action != "stop"
    ):
        parser.error("构建仅适用于 start；测试卷删除仅适用于 stop。")
    docker = Docker(args.docker)
    try:
        docker.local_context()
        if args.action == "start":
            start(docker, build=args.build)
        elif args.action == "check":
            check(docker, load_state(), repeats=args.repeats)
        else:
            stop(docker, load_state(), remove_data=args.remove_test_data)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print(
            "v1.0 操作未完成，请核对本次状态、端口、Docker 权限和服务。",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
