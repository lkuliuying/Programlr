from config.environment import (
    broker,
    database,
    import_limit,
    local_origin,
    model_options,
    positive_integer,
    value,
)
from config.settings import base
from config.settings.base import *  # noqa: F403

MODEL_OPTIONS = model_options()

APP_ORIGIN = local_origin()
APP_AUTHORITY = APP_ORIGIN.removeprefix("http://")
ALLOWED_HOSTS = ["127.0.0.1"]
SECRET_KEY = value("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("DJANGO_SECRET_KEY 长度不足。")
DATABASES = {"default": database()}
CELERY_BROKER_URL = broker()
JOB_QUEUE_TIMEOUT_SECONDS = positive_integer("JOB_QUEUE_TIMEOUT_SECONDS", 300)
JOB_EXECUTION_TIMEOUT_SECONDS = positive_integer("JOB_EXECUTION_TIMEOUT_SECONDS", 300)
CELERY_TASK_ANNOTATIONS = {
    name: {
        "time_limit": JOB_EXECUTION_TIMEOUT_SECONDS,
        "soft_time_limit": max(1, JOB_EXECUTION_TIMEOUT_SECONDS - 10),
    }
    for name in base.CELERY_TASK_ANNOTATIONS
}
IMPORT_LIMITS = {
    name: import_limit("IMPORT_MAX_" + name.upper(), default)
    for name, default in base.IMPORT_LIMITS.items()
}
if positive_integer("WORKER_CONCURRENCY", 1) != 1:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("当前版本只验证了一个 Worker 执行槽位。")
