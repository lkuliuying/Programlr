"""使用已有镜像和独立临时数据库运行后端验收，不读取工作台凭据或数据卷。"""

import argparse
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LAB_BOOT = """
import os, sys
import config.settings.labs_test as settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'v02_labs', 'USER': 'v02_verify', 'HOST': os.environ['VERIFY_POSTGRES'], 'PORT': 5432}}
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.labs_test'
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=0, interactive=False)
sys.argv = ['gunicorn', 'config.wsgi:application', '--bind', '0.0.0.0:8000', '--workers', '2', '--error-logfile', '-']
from gunicorn.app.wsgiapp import run
run()
"""


def main(*, revision: str = "v02", init: bool = False) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--image", default="learning-lab-backend:m5-verify")
    parser.add_argument(
        "--labs", action="store_true", help="启动隔离的固定教学实验服务供完整回归"
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        command = [
            "python",
            "-B",
            "-m",
            "pytest",
            "apps/analysis/tests",
            "--ds=config.settings.local",
            "-q",
            "-p",
            "no:cacheprovider",
        ]
    tag = f"learning-lab-{revision}-check-" + uuid.uuid4().hex[:12]
    network, postgres, redis = tag + "-network", tag + "-postgres", tag + "-redis"
    environment = {
        **os.environ,
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "DATABASE_URL": f"postgresql://v02_verify@{postgres}:5432/v02_verify",
        "DATABASE_PASSWORD": secrets.token_urlsafe(32),
        "CELERY_BROKER_URL": f"redis://{redis}:6379/0",
        "APP_ORIGIN": "http://127.0.0.1:5173",
        "APP_PORT": "5173",
        "MODEL_BASE_URL": "",
        "MODEL_NAME": "",
        "MODEL_API_KEY": "",
        "IMPORT_STORAGE_ROOT": "/tmp/v02-imports",
    }
    created: list[str] = []
    network_created = False
    result_code = 0

    def docker(*values: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [args.docker, *values],
            env=environment,
            text=True,
            encoding="utf-8",
            capture_output=capture,
            timeout=600,
            check=True,
        )

    try:
        docker(
            "network",
            "create",
            "--internal",
            "--label",
            f"learning-lab.check={revision}",
            network,
            capture=True,
        )
        network_created = True
        docker(
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            postgres,
            "--label",
            f"learning-lab.check={revision}",
            "--network",
            network,
            "--tmpfs",
            "/var/lib/postgresql/data",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "POSTGRES_USER=v02_verify",
            "-e",
            "POSTGRES_DB=v02_verify",
            "postgres:17.9-bookworm",
            capture=True,
        )
        created.append(postgres)
        docker(
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            redis,
            "--label",
            f"learning-lab.check={revision}",
            "--network",
            network,
            "redis:7.2.13-bookworm",
            capture=True,
        )
        created.append(redis)
        for _ in range(60):
            ready = subprocess.run(
                [args.docker, "exec", postgres, "pg_isready", "-U", "v02_verify"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("独立数据库未在期限内就绪。")
        if args.labs:
            docker(
                "exec",
                postgres,
                "createdb",
                "-U",
                "v02_verify",
                "v02_labs",
                capture=True,
            )
            lab = tag + "-labs"
            created.append(lab)
            docker(
                "run",
                "-d",
                "--pull",
                "never",
                "--name",
                lab,
                "--label",
                f"learning-lab.check={revision}",
                "--network",
                network,
                "--network-alias",
                "task-board-api",
                "-e",
                "VERIFY_POSTGRES=" + postgres,
                "learning-lab-task-board-backend:m5-verify",
                "python",
                "-B",
                "-c",
                LAB_BOOT,
                capture=True,
            )
            for _ in range(60):
                probe = subprocess.run(
                    [
                        args.docker,
                        "exec",
                        lab,
                        "python",
                        "-c",
                        "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/tasks/', headers={'Host':'127.0.0.1:5174'}), timeout=2).close()",
                    ],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if probe.returncode == 0:
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError("固定实验服务未在期限内就绪。")
        runner = tag + "-runner"
        values = [
            "run",
            "--name",
            runner,
            "--pull",
            "never",
            "--network",
            network,
            "--label",
            f"learning-lab.check={revision}",
            "-w",
            "/workspace/backend",
        ]
        if init:
            values.append("--init")
        for directory in (
            "backend",
            "analyzers",
            "contracts",
            "testdata",
            "scripts",
            "content",
            "examples",
        ):
            values.extend(
                [
                    "--mount",
                    f"type=bind,source={(ROOT / directory).as_posix()},target=/workspace/{directory},readonly",
                ]
            )
        for name in (
            "DJANGO_SECRET_KEY",
            "DATABASE_URL",
            "DATABASE_PASSWORD",
            "CELERY_BROKER_URL",
            "APP_ORIGIN",
            "APP_PORT",
            "MODEL_BASE_URL",
            "MODEL_NAME",
            "MODEL_API_KEY",
            "IMPORT_STORAGE_ROOT",
        ):
            values.extend(["-e", name])
        # 不挂载真实配置、存储卷或模型密钥；只有本次内部网络使用免密码临时数据库。
        print("独立 Linux/PostgreSQL 检查：" + " ".join(command), flush=True)
        created.append(runner)
        docker(*values, args.image, *command)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
        RuntimeError,
    ) as exc:
        print("独立检查未通过，错误类型：" + type(exc).__name__, file=sys.stderr)
        result_code = 1
    finally:
        cleanup_failed = False
        for name in reversed(created):
            result = subprocess.run(
                [args.docker, "rm", "-f", name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            cleanup_failed |= result.returncode != 0
        if network_created:
            result = subprocess.run(
                [args.docker, "network", "rm", network],
                capture_output=True,
                timeout=30,
                check=False,
            )
            cleanup_failed |= result.returncode != 0
        if cleanup_failed:
            print(
                f"本次临时环境清理未确认，请检查标签 learning-lab.check={revision}。",
                file=sys.stderr,
            )
            result_code = 1
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
