import secrets

from config.settings.base import *  # noqa: F403

# 仅用于类型和契约检查；数据库测试使用独立 PostgreSQL 服务。
SECRET_KEY = secrets.token_urlsafe(64)
DATABASES: dict[str, object] = {}
