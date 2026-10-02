import pytest

from apps.tasks.tests.test_contract import assert_response, contract_schema
from apps.tasks.tests.test_tasks import client_with_token, submit

pytestmark = pytest.mark.django_db


def test_persisted_creation_replay_conflict_and_page_match_contract() -> None:
    schema = contract_schema()
    client = client_with_token()
    path = "/api/v1/tasks/"
    key = "5a8f5a8e-ad52-4c23-8e4e-e61d2dd8dfe0"
    first = submit(client, {"title": " 契约测试 "}, key)
    assert first.status_code == 201
    assert_response(first, schema, path, "post")
    replay = submit(client, {"title": "契约测试"}, key)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert_response(replay, schema, path, "post")
    conflict = submit(client, {"title": "冲突输入"}, key)
    assert conflict.status_code == 409
    assert_response(conflict, schema, path, "post")
    page = client.get(path)
    assert page.json()["results"] == [first.json()]
    assert_response(page, schema, path)
