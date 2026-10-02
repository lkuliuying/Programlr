import uuid

from apps.tasks.models import Task
from common.errors import Conflict


def create_task(title: str, key: uuid.UUID) -> tuple[Task, bool]:
    # 唯一键与 get_or_create 的事务保护并发；规范化标题即本动作的比较摘要。
    task, created = Task.objects.get_or_create(
        idempotency_key=key, defaults={"title": title}
    )
    if task.title != title:
        raise Conflict()
    return task, created
