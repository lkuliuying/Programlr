import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def value(name: str) -> str:
    raw = os.environ.get(name, "")
    file_name = os.environ.get(f"{name}_FILE")
    if file_name:
        if raw:
            raise ImproperlyConfigured(f"{name} 与文件配置不能同时提供。")
        try:
            raw = Path(file_name).read_text(encoding="utf-8").strip()
        except OSError:
            raise ImproperlyConfigured(f"{name} 的配置文件不可读取。") from None
    if not raw or raw.startswith("__"):
        raise ImproperlyConfigured(f"必须配置有效的 {name}。")
    return raw


def positive_integer(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 3600:
        raise ImproperlyConfigured(f"{name} 必须为 1 至 3600 的整数。")
    return int(raw)


def local_origin() -> str:
    port = os.environ.get("APP_PORT", "5173")
    if not port.isascii() or not port.isdecimal() or not 1024 <= int(port) <= 65535:
        raise ImproperlyConfigured("APP_PORT 必须为 1024 至 65535 的整数。")
    if os.environ.get("APP_HOST", "127.0.0.1") != "127.0.0.1":
        raise ImproperlyConfigured("APP_HOST 仅支持 IPv4 回环地址。")
    expected = f"http://127.0.0.1:{port}"
    if os.environ.get("APP_ORIGIN", expected) != expected:
        raise ImproperlyConfigured("APP_ORIGIN 必须与本地入口精确一致。")
    return expected


def database() -> dict[str, Any]:
    try:
        url = urlsplit(value("DATABASE_URL"))
        if (
            url.scheme != "postgresql"
            or not url.hostname
            or not url.username
            or url.path in ("", "/")
            or url.query
            or url.fragment
        ):
            raise ValueError
        password = unquote(url.password) if url.password else value("DATABASE_PASSWORD")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(url.path[1:]),
            "USER": unquote(url.username),
            "PASSWORD": password,
            "HOST": url.hostname,
            "PORT": url.port or 5432,
            "CONN_MAX_AGE": 0,
            "OPTIONS": {"connect_timeout": 3, "options": "-c statement_timeout=5000"},
        }
    except ValueError:
        raise ImproperlyConfigured("DATABASE_URL 格式无效。") from None


def broker() -> str:
    raw = value("CELERY_BROKER_URL")
    try:
        parsed = urlsplit(raw)
        if parsed.scheme != "redis" or not parsed.hostname or not parsed.port:
            raise ValueError
        if parsed.query or parsed.fragment or parsed.path != "/0":
            raise ValueError
    except ValueError:
        raise ImproperlyConfigured("CELERY_BROKER_URL 格式无效。") from None
    return raw


def import_limit(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if (
        len(raw) > 10
        or not raw.isascii()
        or not raw.isdecimal()
        or not 1 <= int(raw) <= default
    ):
        raise ImproperlyConfigured(f"{name} 必须为正整数且不得超过已验证的默认上限。")
    return int(raw)


def model_options() -> dict[str, str]:
    """模型是可选能力；延迟验证避免错误配置阻止静态浏览和学习启动。"""
    return {
        name: os.environ.get(env, default)
        for name, env, default in (
            ("base_url", "MODEL_BASE_URL", ""),
            ("model", "MODEL_NAME", ""),
        )
    }
