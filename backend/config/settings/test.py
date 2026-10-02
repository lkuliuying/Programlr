import secrets

from config.settings.base import *  # noqa: F403

# 仅供无服务配置的契约导出和类型检查；数据库测试显式使用 local 配置。
SECRET_KEY = secrets.token_urlsafe(64)
APP_ORIGIN = "http://127.0.0.1:5173"
APP_AUTHORITY = "127.0.0.1:5173"
ALLOWED_HOSTS = ["127.0.0.1"]
DATABASES: dict[str, object] = {}
CELERY_BROKER_URL = "redis://redis:6379/0"
JOB_QUEUE_TIMEOUT_SECONDS = 300
JOB_EXECUTION_TIMEOUT_SECONDS = 300
