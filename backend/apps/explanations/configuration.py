import hashlib
import json
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from common.errors import ApiProblem
from config.environment import value


@dataclass(frozen=True)
class ModelConfiguration:
    base_url: str
    model: str

    def binding(self) -> dict[str, str | int]:
        return asdict(self)


def digest(value: object) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def encode(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def configuration() -> ModelConfiguration:
    options = settings.MODEL_OPTIONS
    if not options.get("base_url") or not options.get("model"):
        raise ApiProblem(
            409,
            "MODEL_NOT_CONFIGURED",
            "模型地址或模型 ID 未配置，静态浏览和练习仍可使用。",
        )
    try:
        base = options["base_url"]
        parsed = urlsplit(base)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or any(c.isspace() for c in base)
            or "\\" in base
            or parsed.port == 0
        ):
            raise ValueError
        model = options["model"]
        if (
            not isinstance(model, str)
            or not 1 <= len(model) <= 200
            or model.startswith("__")
            or any(ord(c) < 33 for c in model)
        ):
            raise ValueError
        return ModelConfiguration(base.rstrip("/"), model)
    except (KeyError, TypeError, ValueError):
        raise ApiProblem(
            409,
            "MODEL_CONFIGURATION_INVALID",
            "模型配置无效，请核对服务端配置；静态功能不受影响。",
        ) from None


def credential() -> str:
    try:
        key = value("MODEL_API_KEY")
        if len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
            raise ValueError
        return key
    except (ImproperlyConfigured, ValueError):
        raise ApiProblem(409, "MODEL_NOT_CONFIGURED", "模型凭据未正确配置。") from None
