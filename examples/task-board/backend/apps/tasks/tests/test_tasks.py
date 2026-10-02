import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any
from unittest.mock import patch

import pytest
from django.db import DatabaseError, IntegrityError, close_old_connections, transaction
from rest_framework.test import APIClient

from apps.tasks.models import Task
from apps.tasks.services import create_task

pytestmark = pytest.mark.django_db
HOST = "127.0.0.1:5174"
ORIGIN = f"http://{HOST}"
PATH = "/api/v1/tasks/"


def client_with_token() -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/csrf/", HTTP_HOST=HOST)
    assert response.status_code == 200
    client.credentials(
        HTTP_HOST=HOST,
        HTTP_ORIGIN=ORIGIN,
        HTTP_X_CSRFTOKEN=response.json()["csrf_token"],
    )
    return client


def submit(client: APIClient, payload: Any, key: str | None = None) -> Any:
    return client.post(
        PATH, payload, format="json", HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4())
    )


@pytest.mark.parametrize(
    "title", ["学习请求校验", "  阅读源码  ", "字" * 200, "😀" * 200]
)
def test_title_persisted_and_read_after_new_client(title: str) -> None:
    response = submit(client_with_token(), {"title": title})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "created_at"}
    assert body["title"] == title.strip()
    assert body["created_at"].endswith("Z")
    assert Task.objects.count() == 1
    assert str(Task.objects.get().pk) == body["id"]
    assert client_with_token().get(PATH).json()["results"] == [body]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": " \t\n "},
        {"title": "\u3000\u00a0"},
        {"title": None},
        {"title": 12},
        {"title": False},
        {"title": []},
        {"title": {}},
        {"title": "x" * 201},
        {"title": "a\x00b"},
        {"title": "正常", "extra": True},
        {"id": "forged", "title": "正常"},
        [],
    ],
)
def test_invalid_input_never_writes(payload: Any) -> None:
    response = submit(client_with_token(), payload)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response["X-Request-ID"]
    assert response.json()["details"]["fields"]
    assert Task.objects.count() == 0


def test_replay_and_conflict() -> None:
    client = client_with_token()
    key = str(uuid.uuid4())
    first = submit(client, {"title": " 原标题 "}, key)
    replay = submit(client, {"title": "原标题"}, key)
    assert first.status_code == 201 and replay.status_code == 200
    assert first.json() == replay.json()
    conflict = submit(client, {"title": "不同标题"}, key)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert Task.objects.count() == 1
    assert submit(client, {"title": "原标题"}).status_code == 201
    assert Task.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_create_once() -> None:
    key = str(uuid.uuid4())
    gate = Barrier(2)

    def write() -> tuple[int, str]:
        close_old_connections()
        try:
            client = client_with_token()
            gate.wait(timeout=10)
            response = submit(client, {"title": "并发标题"}, key)
            return response.status_code, response.json()["id"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: write(), range(2)))
    assert sorted(item[0] for item in results) == [200, 201]
    assert results[0][1] == results[1][1]
    assert Task.objects.count() == 1


@pytest.mark.parametrize("title", ["", " \t\n"])
def test_database_constraint_rejects_blank_without_serializer(title: str) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.create(title=title, idempotency_key=uuid.uuid4())
    assert Task.objects.count() == 0


@pytest.mark.parametrize(
    "host,origin,token",
    [
        (HOST, ORIGIN, False),
        (HOST, "", True),
        (HOST, "http://evil.invalid", True),
        (HOST, "http://127.0.0.1:5173", True),
        ("evil.invalid:5174", ORIGIN, True),
        ("127.0.0.1:5173", ORIGIN, True),
    ],
)
def test_anonymous_boundary(host: str, origin: str, token: bool) -> None:
    client = client_with_token()
    csrf = client.get("/api/v1/csrf/").json()["csrf_token"]
    headers = {"HTTP_HOST": host, "HTTP_ORIGIN": origin}
    if token:
        headers["HTTP_X_CSRFTOKEN"] = csrf
    client.credentials(**headers)
    response = submit(client, {"title": "应被拒绝"})
    assert response.status_code == 403
    assert Task.objects.count() == 0


def test_distinct_cookie_and_no_cache() -> None:
    response = APIClient().get("/api/v1/csrf/", HTTP_HOST=HOST)
    cookie = response.cookies["task_board_csrftoken"]
    assert cookie["samesite"] == "Strict" and cookie["httponly"]
    assert not cookie["domain"]
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "query", ["page=0", "page=x", "page=1&page=2", "page_size=101", "unknown=1"]
)
def test_invalid_pagination(query: str) -> None:
    assert client_with_token().get(PATH + "?" + query).status_code == 400


def test_pagination_and_empty_page() -> None:
    client = client_with_token()
    assert client.get(PATH).json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }
    assert client.get(PATH + "?page=2").json()["code"] == "PAGE_NOT_FOUND"
    for title in ["第一条", "第二条", "第三条"]:
        create_task(title, uuid.uuid4())
    response = client.get(PATH + "?page_size=2").json()
    assert [task["title"] for task in response["results"]] == ["第三条", "第二条"]
    assert response["next"] == PATH + "?page=2&page_size=2"
    assert client.get(response["next"]).json()["results"][0]["title"] == "第一条"


@pytest.mark.parametrize("key", ["", "not-uuid"])
def test_invalid_key(key: str) -> None:
    response = client_with_token().post(
        PATH, {"title": "正常"}, format="json", HTTP_IDEMPOTENCY_KEY=key
    )
    assert response.status_code == 400 and Task.objects.count() == 0


def test_content_type_malformed_and_size() -> None:
    client = client_with_token()
    assert client.post(PATH, "{", content_type="application/json").status_code == 400
    assert client.post(PATH, "title=x", content_type="text/plain").status_code == 415
    assert (
        client.post(
            PATH, '{"title":"' + "x" * 5000 + '"}', content_type="application/json"
        ).status_code
        == 413
    )
    assert Task.objects.count() == 0


def test_database_failure_is_explicit_and_redacted() -> None:
    with patch(
        "apps.tasks.services.Task.objects.get_or_create",
        side_effect=DatabaseError("synthetic-private-detail"),
    ):
        response = submit(client_with_token(), {"title": "正常"})
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert b"synthetic-private-detail" not in response.content
    assert Task.objects.count() == 0
