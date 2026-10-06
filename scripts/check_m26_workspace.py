"""管理 M26 独立浏览器验收栈，只操作本次 UUID 标签的本地临时资源。"""

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime/m26-verify/state.json"
ORIGIN = "http://127.0.0.1:5185"
LABEL = "learning-lab.m26-verify"
TAG = re.compile(r"learning-lab-m26-verify-[a-f0-9]{12}\Z")
ROLES = (
    "postgres",
    "redis",
    "initialize",
    "migrate",
    "api",
    "worker",
    "reconciler",
    "frontend",
)
BACKEND_IMAGE = "learning-lab-backend:m5-verify"
FRONTEND_IMAGE = "learning-lab-frontend:m5-verify"
ENVIRONMENT = (
    "DJANGO_SETTINGS_MODULE",
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
    "DATABASE_PASSWORD",
    "CELERY_BROKER_URL",
    "APP_ORIGIN",
    "APP_PORT",
    "APP_HOST",
    "IMPORT_STORAGE_ROOT",
    "MODEL_BASE_URL",
    "MODEL_NAME",
    "MODEL_API_KEY",
    "WORKER_CONCURRENCY",
)


def validate_state(value: Any) -> dict[str, Any]:
    base_keys = {
        "version",
        "tag",
        "origin",
        "status",
        "containers",
        "network",
        "volume",
    }
    if (
        not isinstance(value, dict)
        or (
            (value.get("version") == 1 and set(value) != base_keys)
            or (
                value.get("version") == 2
                and set(value) != base_keys | {"entry_network"}
            )
            or value.get("version") not in {1, 2}
        )
        or not isinstance(value["tag"], str)
        or not TAG.fullmatch(value["tag"])
        or value["origin"] != ORIGIN
        or value["status"] not in {"starting", "ready", "failed", "stopped"}
    ):
        raise RuntimeError("M26 验收状态无效，拒绝操作资源。")
    tag = value["tag"]
    if (
        value["containers"] != [f"{tag}-{role}" for role in ROLES]
        or value["network"] != tag + "-network"
        or value["volume"] != tag + "-imports"
        or (value["version"] == 2 and value["entry_network"] != tag + "-entry")
    ):
        raise RuntimeError("M26 资源名称不符合本次所有权边界。")
    return value


def save_state(value: dict[str, Any]) -> None:
    validate_state(value)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(STATE)


def load_state() -> dict[str, Any]:
    try:
        return validate_state(json.loads(STATE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        raise RuntimeError("M26 状态文件不可读，请核对本次验收状态。") from None


class Docker:
    def __init__(self, executable: str) -> None:
        self.executable = executable
        self.environment = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith(
                (
                    "COMPOSE_",
                    "MODEL_",
                    "DATABASE_",
                    "DJANGO_",
                    "APP_",
                    "CELERY_",
                    "IMPORT_",
                    "WORKER_",
                )
            )
            and name not in {"DOCKER_HOST", "DOCKER_CONTEXT"}
        }

    def call(self, *values: str, timeout: int = 90) -> str:
        try:
            result = subprocess.run(
                [self.executable, *values],
                env=self.environment,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout,
                check=True,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            # Docker 原始错误可能含配置，不复制命令或容器环境到终端。
            raise RuntimeError(
                "M26 Docker 命令未确认完成；状态已保留，可用 status 核对。"
            ) from None

    def local_context(self) -> None:
        endpoint = self.call(
            "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"
        )
        if not endpoint.startswith(("npipe://", "unix://")):
            raise RuntimeError("M26 验收只允许本机 Docker socket。")

    def owned(self, state: dict[str, Any]) -> dict[str, list[str]]:
        validate_state(state)
        output: dict[str, list[str]] = {}
        for kind in ("container", "network", "volume"):
            command = ("ps", "-aq") if kind == "container" else (kind, "ls", "-q")
            identities = self.call(
                *command, "--filter", f"label={LABEL}={state['tag']}"
            ).splitlines()
            names = []
            expected = state["containers"] if kind == "container" else [state[kind]]
            if kind == "network" and "entry_network" in state:
                expected = [*expected, state["entry_network"]]
            for identity in identities:
                name = json.loads(
                    self.call(kind, "inspect", "--format", "{{json .Name}}", identity)
                ).removeprefix("/")
                labels = json.loads(
                    self.call(
                        kind,
                        "inspect",
                        "--format",
                        "{{json .Config.Labels}}"
                        if kind == "container"
                        else "{{json .Labels}}",
                        identity,
                    )
                )
                role = name.removeprefix(state["tag"] + "-")
                if (
                    name not in expected
                    or not isinstance(labels, dict)
                    or labels.get(LABEL) != state["tag"]
                    or labels.get(LABEL + ".role") != role
                ):
                    raise RuntimeError("M26 资源标签或名称不一致，拒绝清理。")
                names.append(name)
            output[kind] = names
            all_command = ("ps", "-a") if kind == "container" else (kind, "ls")
            known_names = set(
                self.call(
                    *all_command,
                    "--format",
                    "{{.Names}}" if kind == "container" else "{{.Name}}",
                ).splitlines()
            )
            if (set(expected) & known_names) - set(names):
                raise RuntimeError("本次预期名称已被不同标签资源占用，拒绝接管或清理。")
        return output


def labels(state: dict[str, Any], role: str) -> list[str]:
    return ["--label", f"{LABEL}={state['tag']}", "--label", f"{LABEL}.role={role}"]


def backend_options(state: dict[str, Any], role: str) -> list[str]:
    values = [
        "run",
        "--pull",
        "never",
        "--name",
        f"{state['tag']}-{role}",
        *labels(state, role),
        "--network",
        state["network"],
        "--init",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=256m",
        "--security-opt",
        "no-new-privileges:true",
        "-w",
        "/workspace/backend",
        "-e",
        "HOME=/tmp",
        "--mount",
        f"type=volume,source={state['volume']},target=/var/lib/learning-lab/imports",
    ]
    for directory in ("backend", "analyzers", "contracts", "content", "examples"):
        values.extend(
            [
                "--mount",
                f"type=bind,source={(ROOT / directory).as_posix()},target=/workspace/{directory},readonly",
            ]
        )
    for name in ENVIRONMENT:
        values.extend(["-e", name])
    return values


def wait_postgres(docker: Docker, name: str) -> None:
    for _ in range(60):
        try:
            docker.call("exec", name, "pg_isready", "-U", "m26_verify", timeout=5)
            return
        except RuntimeError:
            time.sleep(0.5)
    raise RuntimeError("M26 临时数据库未在期限内就绪。")


def wait_http() -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        try:
            with opener.open(ORIGIN + "/api/v1/csrf/", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise RuntimeError("M26 本地 HTTP 未在期限内就绪。")


def start(docker: Docker) -> dict[str, Any]:
    if STATE.exists() and load_state()["status"] != "stopped":
        raise RuntimeError("已有 M26 验收状态，请先 status 或 stop，不能覆盖。")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("当前前端 dist 不存在，请先完成已授权的前端构建。")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 5185))
    for image in (
        BACKEND_IMAGE,
        FRONTEND_IMAGE,
        "postgres:17.9-bookworm",
        "redis:7.2.13-bookworm",
    ):
        docker.call("image", "inspect", "--format", "{{.Id}}", image)
    tag = "learning-lab-m26-verify-" + uuid.uuid4().hex[:12]
    state: dict[str, Any] = {
        "version": 2,
        "tag": tag,
        "origin": ORIGIN,
        "status": "starting",
        "containers": [f"{tag}-{role}" for role in ROLES],
        "network": tag + "-network",
        "entry_network": tag + "-entry",
        "volume": tag + "-imports",
    }
    save_state(state)
    docker.environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.local",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DATABASE_URL": f"postgresql://m26_verify@{tag}-postgres:5432/m26_verify",
            "DATABASE_PASSWORD": "m26-ephemeral-isolated",
            "CELERY_BROKER_URL": f"redis://{tag}-redis:6379/0",
            "APP_ORIGIN": ORIGIN,
            "APP_PORT": "5185",
            "APP_HOST": "127.0.0.1",
            "APP_AUTHORITY": "127.0.0.1:5185",
            "IMPORT_STORAGE_ROOT": "/var/lib/learning-lab/imports",
            "MODEL_BASE_URL": "",
            "MODEL_NAME": "",
            "MODEL_API_KEY": "",
            "WORKER_CONCURRENCY": "1",
        }
    )
    try:
        docker.call(
            "network",
            "create",
            "--internal",
            *labels(state, "network"),
            state["network"],
        )
        docker.call(
            "network", "create", *labels(state, "entry"), state["entry_network"]
        )
        docker.call("volume", "create", *labels(state, "imports"), state["volume"])
        docker.call(
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            tag + "-postgres",
            *labels(state, "postgres"),
            "--network",
            state["network"],
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "POSTGRES_USER=m26_verify",
            "-e",
            "POSTGRES_DB=m26_verify",
            "postgres:17.9-bookworm",
        )
        docker.call(
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            tag + "-redis",
            *labels(state, "redis"),
            "--network",
            state["network"],
            "redis:7.2.13-bookworm",
        )
        wait_postgres(docker, tag + "-postgres")
        docker.call(
            *backend_options(state, "initialize"),
            "--user",
            "0:0",
            BACKEND_IMAGE,
            "python",
            "-B",
            "-c",
            "import os; os.chown('/var/lib/learning-lab/imports',1000,1000); os.chmod('/var/lib/learning-lab/imports',0o700)",
        )
        docker.call(
            *backend_options(state, "migrate"),
            BACKEND_IMAGE,
            "python",
            "-B",
            "-c",
            "import django; django.setup(); from django.core.management import call_command; call_command('migrate',interactive=False,verbosity=0); call_command('load_learning_content',verbosity=0)",
            timeout=120,
        )
        commands = {
            "api": [
                "gunicorn",
                "config.wsgi:application",
                "--bind",
                "0.0.0.0:8000",
                "--workers",
                "2",
                "--timeout",
                "15",
                "--error-logfile",
                "-",
            ],
            "worker": [
                "celery",
                "-A",
                "config.celery:app",
                "worker",
                "--loglevel=WARNING",
                "--concurrency=1",
                "--without-gossip",
                "--without-mingle",
            ],
            "reconciler": ["python", "-B", "manage.py", "reconcile_jobs", "--loop"],
        }
        for role, command in commands.items():
            values = backend_options(state, role)
            values.insert(1, "-d")
            if role == "api":
                values.extend(["--network-alias", "api"])
            docker.call(*values, BACKEND_IMAGE, *command)
        docker.call(
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            tag + "-frontend",
            *labels(state, "frontend"),
            "--network",
            state["network"],
            "-p",
            "127.0.0.1:5185:8080",
            "-e",
            "APP_AUTHORITY",
            "--mount",
            f"type=bind,source={(ROOT / 'frontend/dist').as_posix()},target=/usr/share/nginx/html,readonly",
            "--mount",
            f"type=bind,source={(ROOT / 'infra/nginx/default.conf.template').as_posix()},target=/etc/nginx/templates/default.conf.template,readonly",
            FRONTEND_IMAGE,
        )
        # 数据服务仅连接内部网络，前端另接本机发布端口所需的入口网络。
        docker.call("network", "connect", state["entry_network"], tag + "-frontend")
        wait_http()
        state["status"] = "ready"
        save_state(state)
        return state
    except Exception:
        # 未确认完成的资源不自动删除；下一次只凭名称和标签复核本次资源。
        state["status"] = "failed"
        save_state(state)
        raise


def stop(docker: Docker, state: dict[str, Any]) -> None:
    owned = docker.owned(state)
    for name in reversed(owned["container"]):
        docker.call("container", "rm", "-f", name)
    for name in owned["network"]:
        docker.call("network", "rm", name)
    for name in owned["volume"]:
        docker.call("volume", "rm", name)
    if any(docker.owned(state).values()):
        raise RuntimeError("M26 清理结果未确认，状态文件已保留。")
    state["status"] = "stopped"
    save_state(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop"])
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    docker = Docker(args.docker)
    try:
        docker.local_context()
        if args.action == "start":
            state = start(docker)
            print(f"M26 独立验收栈已就绪：{state['origin']}")
        elif args.action == "stop":
            stop(docker, load_state())
            print("M26 本次验收容器、网络和测试卷已清理。")
        else:
            state = load_state()
            owned = docker.owned(state)
            print(f"M26 状态：{state['status']}；入口：{state['origin']}")
            for name in owned["container"]:
                status = docker.call(
                    "container", "inspect", "--format", "{{.State.Status}}", name
                )
                print(f"{name}: {status}")
        return 0
    except (RuntimeError, OSError, ValueError, TypeError) as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print(
            f"M26 操作未完成：{message}。本次状态保留供核对。",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
