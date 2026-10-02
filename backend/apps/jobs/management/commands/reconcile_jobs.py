import signal
import threading
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand
from django.db import DatabaseError, close_old_connections

from apps.jobs.services import reconcile_expired
from apps.projects.exceptions import ImportRejected
from apps.projects.services import reconcile_import_storage


class Command(BaseCommand):
    help = "核对超期任务；独立进程不依赖 Redis 或 Worker 存活。"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        stopped = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stopped.set())
        while not stopped.is_set():
            try:
                close_old_connections()
                count = reconcile_expired()
                reconcile_import_storage()
                if count:
                    self.stdout.write(f"已终结 {count} 个超期任务。")
            except DatabaseError:
                self.stderr.write("数据库暂不可用，本轮核对失败。")
                if not options["loop"]:
                    raise
            except (OSError, ImportRejected):
                self.stderr.write("导入存储暂不可用，本轮清理失败。")
                if not options["loop"]:
                    raise
            finally:
                close_old_connections()
            if not options["loop"] or stopped.wait(5):
                break
