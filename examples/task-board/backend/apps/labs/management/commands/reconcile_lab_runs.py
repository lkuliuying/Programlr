import logging
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import DatabaseError, close_old_connections

from apps.labs.services import reconcile_runs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "关闭过期实验并清理该运行的数据，保留关闭记录。"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--loop", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        while True:
            try:
                reconcile_runs()
            except DatabaseError:
                logger.error("实验清理数据库不可用，等待下次核对。")
                if not options["loop"]:
                    raise
            finally:
                close_old_connections()
            if not options["loop"]:
                return
            time.sleep(5)
