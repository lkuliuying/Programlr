"""启动或清理本版独立回环验收实例，仅管理自身标签资源，不读取真实配置。"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from check_v02_backend import LAB_BOOT

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime/v03-development-20261001/browser-stack.json"
LABEL = "learning-lab.check=v03-browser"
ORIGIN = "http://127.0.0.1:5180"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop"])
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    environment = {
        **os.environ,
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "DATABASE_PASSWORD": secrets.token_urlsafe(32),
        "DATABASE_URL": "postgresql://v02_verify@postgres:5432/v02_verify",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "DJANGO_SETTINGS_MODULE": "config.settings.local",
        "APP_ORIGIN": ORIGIN,
        "APP_PORT": "5180",
        "APP_HOST": "127.0.0.1",
        "MODEL_BASE_URL": "",
        "MODEL_NAME": "",
        "MODEL_API_KEY": "",
    }

    def docker(*values: str, timeout: int = 90) -> str:
        return subprocess.run(
            [args.docker, *values],
            env=environment,
            text=True,
            encoding="utf-8",
            check=True,
            capture_output=True,
            timeout=timeout,
        ).stdout.strip()

    def stop(state: dict[str, Any]) -> None:
        for name in reversed(state["containers"]):
            result = subprocess.run(
                [
                    args.docker,
                    "inspect",
                    "--format",
                    '{{index .Config.Labels "learning-lab.check"}}',
                    name,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode and "No such" in result.stderr:
                continue
            if result.returncode or result.stdout.strip() != "v03-browser":
                raise RuntimeError("拒绝清理标签无法确认的资源。")
            docker("rm", "-f", name, timeout=30)
        for kind, name in (
            ("volume", state["volume"]),
            ("network", state["network"]),
            ("network", state["entry_network"]),
        ):
            label = docker(
                kind,
                "inspect",
                "--format",
                '{{index .Labels "learning-lab.check"}}',
                name,
            )
            if label != "v03-browser":
                raise RuntimeError("拒绝清理非本版验收资源。")
            docker(kind, "rm", name, timeout=30)
        state["closed"] = True
        STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    if args.action == "stop":
        existing_state = json.loads(STATE.read_text(encoding="utf-8"))
        if not existing_state.get("closed"):
            stop(existing_state)
        print("本版独立验收实例已清理；原有实例和数据卷未操作。")
        return 0
    if STATE.exists() and not json.loads(STATE.read_text(encoding="utf-8")).get(
        "closed"
    ):
        raise RuntimeError("验收实例已有状态，请先核对或复用，不创建重复实例。")
    if not (ROOT / "frontend/dist/index.html").exists():
        raise RuntimeError("请先构建当前前端。")
    with socket.socket() as port:
        port.bind(("127.0.0.1", 5180))
    tag = "learning-lab-v03-ui-" + uuid.uuid4().hex[:12]
    state: dict[str, Any] = {
        "origin": ORIGIN,
        "network": tag + "-net",
        "entry_network": tag + "-entry",
        "volume": tag + "-imports",
        "containers": [],
        "closed": False,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def run(
        suffix: str,
        flags: list[str],
        image: str,
        command: tuple[str, ...] = (),
        *,
        detached: bool = True,
    ) -> str:
        name = tag + "-" + suffix
        state["containers"].append(name)
        save()
        values = [
            "run",
            "--pull",
            "never",
            "--name",
            name,
            "--label",
            LABEL,
            "--network",
            state["network"],
            *flags,
        ]
        if detached:
            values.insert(1, "-d")
        docker(*values, image, *command)
        return name

    docker("network", "create", "--internal", "--label", LABEL, state["network"])
    docker("network", "create", "--label", LABEL, state["entry_network"])
    docker("volume", "create", "--label", LABEL, state["volume"])
    save()
    try:
        postgres = run(
            "postgres",
            [
                "--network-alias",
                "postgres",
                "--tmpfs",
                "/var/lib/postgresql/data",
                "-e",
                "POSTGRES_HOST_AUTH_METHOD=trust",
                "-e",
                "POSTGRES_USER=v02_verify",
                "-e",
                "POSTGRES_DB=v02_verify",
            ],
            "postgres:17.9-bookworm",
        )
        run("redis", ["--network-alias", "redis"], "redis:7.2.13-bookworm")
        for _ in range(60):
            if (
                subprocess.run(
                    [args.docker, "exec", postgres, "pg_isready", "-U", "v02_verify"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                ).returncode
                == 0
            ):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("临时数据库未就绪。")
        code: list[str] = []
        for directory in (
            "backend",
            "analyzers",
            "contracts",
            "testdata",
            "content",
            "examples",
            "scripts",
        ):
            code.extend(
                [
                    "--mount",
                    f"type=bind,source={(ROOT / directory).as_posix()},target=/workspace/{directory},readonly",
                ]
            )
        mounts = [
            "--mount",
            f"type=volume,source={state['volume']},target=/var/lib/learning-lab/imports",
        ]
        run(
            "initialize",
            [*mounts, "--user", "0:0"],
            "learning-lab-backend:m5-verify",
            (
                "python",
                "-c",
                "import os; os.chown('/var/lib/learning-lab/imports',1000,1000); os.chmod('/var/lib/learning-lab/imports',0o700)",
            ),
            detached=False,
        )
        common = [
            *mounts,
            *code,
            "-w",
            "/workspace/backend",
            "--init",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--read-only",
            "--tmpfs",
            "/tmp",
            "--security-opt",
            "no-new-privileges:true",
        ]
        for key in (
            "DJANGO_SECRET_KEY",
            "DATABASE_PASSWORD",
            "DATABASE_URL",
            "CELERY_BROKER_URL",
            "DJANGO_SETTINGS_MODULE",
            "APP_ORIGIN",
            "APP_PORT",
            "APP_HOST",
            "MODEL_BASE_URL",
            "MODEL_NAME",
            "MODEL_API_KEY",
        ):
            common.extend(["-e", key])
        run(
            "migrate",
            common,
            "learning-lab-backend:m5-verify",
            ("python", "-B", "manage.py", "migrate", "--noinput"),
            detached=False,
        )
        run(
            "content",
            common,
            "learning-lab-backend:m5-verify",
            ("python", "-B", "manage.py", "load_learning_content"),
            detached=False,
        )
        run(
            "api", [*common, "--network-alias", "api"], "learning-lab-backend:m5-verify"
        )
        run(
            "worker",
            common,
            "learning-lab-backend:m5-verify",
            (
                "celery",
                "-A",
                "config.celery:app",
                "worker",
                "--loglevel=WARNING",
                "--concurrency=1",
                "--without-gossip",
                "--without-mingle",
            ),
        )
        run(
            "reconciler",
            common,
            "learning-lab-backend:m5-verify",
            ("python", "-B", "manage.py", "reconcile_jobs", "--loop"),
        )
        docker("exec", postgres, "createdb", "-U", "v02_verify", "v02_labs")
        lab = run(
            "labs",
            [
                *code,
                "-w",
                "/workspace/examples/task-board/backend",
                "--init",
                "--network-alias",
                "task-board-api",
                "-e",
                "VERIFY_POSTGRES=postgres",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--pids-limit",
                "128",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "--security-opt",
                "no-new-privileges:true",
            ],
            "learning-lab-task-board-backend:m5-verify",
            ("python", "-B", "-c", LAB_BOOT),
        )
        for _ in range(60):
            probe = subprocess.run(
                [
                    args.docker,
                    "exec",
                    lab,
                    "python",
                    "-c",
                    "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/tasks/',headers={'Host':'127.0.0.1:5174'}),timeout=2).close()",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if probe.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("固定实验服务未就绪。")
        run(
            "frontend",
            [
                "--network",
                state["entry_network"],
                "-p",
                "127.0.0.1:5180:8080",
                "-e",
                "APP_AUTHORITY=127.0.0.1:5180",
                "--mount",
                f"type=bind,source={(ROOT / 'frontend/dist').as_posix()},target=/usr/share/nginx/html,readonly",
            ],
            "learning-lab-frontend:m5-verify",
        )
        opener = build_opener(ProxyHandler({}))
        for _ in range(60):
            try:
                with opener.open(ORIGIN + "/api/v1/knowledge-curricula/", timeout=2):
                    break
            except (URLError, TimeoutError):
                time.sleep(0.5)
        else:
            raise RuntimeError("独立工作台未就绪。")
        print("独立 v0.3 验收实例：" + ORIGIN)
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError):
        stop(state)
        raise RuntimeError(
            "独立验收启动未通过，临时资源已清理；未操作原有实例。"
        ) from None


if __name__ == "__main__":
    raise SystemExit(main())
