from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.environment import (
    broker,
    database,
    local_origin,
    model_options,
    positive_integer,
    value,
)


@pytest.mark.parametrize(
    "env",
    [
        {"APP_HOST": "0.0.0.0"},
        {"APP_PORT": "0"},
        {"APP_PORT": "70000"},
        {"APP_ORIGIN": "http://localhost:5173"},
        {"APP_ORIGIN": "http://127.0.0.1:5173/"},
    ],
)
def test_invalid_origin_config(env: dict[str, str]) -> None:
    with patch.dict("os.environ", env, clear=True), pytest.raises(ImproperlyConfigured):
        local_origin()


@pytest.mark.parametrize("raw", ["", "0", "-1", "text", "3601"])
def test_invalid_budget(raw: str) -> None:
    with (
        patch.dict("os.environ", {"JOB_QUEUE_TIMEOUT_SECONDS": raw}, clear=True),
        pytest.raises(ImproperlyConfigured),
    ):
        positive_integer("JOB_QUEUE_TIMEOUT_SECONDS", 300)


def test_placeholders_missing_and_secret_files() -> None:
    for env in (
        {},
        {"DJANGO_SECRET_KEY": "__SET_LOCALLY__"},
        {"DJANGO_SECRET_KEY_FILE": "/missing-file"},
        {"DJANGO_SECRET_KEY": "unused", "DJANGO_SECRET_KEY_FILE": "/missing-file"},
    ):
        with (
            patch.dict("os.environ", env, clear=True),
            pytest.raises(ImproperlyConfigured),
        ):
            value("DJANGO_SECRET_KEY")


@pytest.mark.parametrize(
    "raw",
    [
        "__SET_LOCAL_DATABASE_URL__",
        "sqlite:///db",
        "postgresql:///lab",
        "postgresql://lab@localhost/lab?unsafe=1",
    ],
)
def test_invalid_database_config(raw: str) -> None:
    with (
        patch.dict("os.environ", {"DATABASE_URL": raw}, clear=True),
        pytest.raises(ImproperlyConfigured),
    ):
        database()


@pytest.mark.parametrize(
    "raw",
    [
        "__SET_LOCAL_BROKER_URL__",
        "http://invalid/0",
        "redis://redis/0",
        "redis://redis:6379/1",
    ],
)
def test_invalid_broker_config(raw: str) -> None:
    with (
        patch.dict("os.environ", {"CELERY_BROKER_URL": raw}, clear=True),
        pytest.raises(ImproperlyConfigured),
    ):
        broker()


def test_model_options_only_load_nonsecret_target_and_model() -> None:
    with patch.dict(
        "os.environ",
        {
            "MODEL_BASE_URL": "https://model-test.invalid/v1",
            "MODEL_NAME": "test-model",
            "MODEL_API_KEY": "synthetic-test-only",
            "MODEL_ENABLED": "false",
            "MODEL_TIMEOUT_SECONDS": "1",
            "MODEL_CONTEXT_MAX_BYTES": "1",
            "MODEL_MAX_OUTPUT_TOKENS": "1",
            "MODEL_TOKEN_LIMIT_FIELD": "unknown",
        },
        clear=True,
    ):
        assert model_options() == {
            "base_url": "https://model-test.invalid/v1",
            "model": "test-model",
        }
