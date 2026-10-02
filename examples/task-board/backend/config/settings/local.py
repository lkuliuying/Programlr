import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403


def read_secret(name: str) -> str:
    path = os.environ.get(name)
    if not path:
        raise ImproperlyConfigured(f"必须配置 {name}。")
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        raise ImproperlyConfigured(f"无法读取 {name}。") from None
    if len(value) < 32:
        raise ImproperlyConfigured(f"{name} 的配置无效。")
    return value


SECRET_KEY = read_secret("DJANGO_SECRET_KEY_FILE")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "task_board",
        "USER": "task_board",
        "PASSWORD": read_secret("DATABASE_PASSWORD_FILE"),
        "HOST": "task-board-postgres",
        "PORT": 5432,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 3, "options": "-c statement_timeout=5000"},
    }
}
