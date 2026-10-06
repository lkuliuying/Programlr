from typing import Any

import pytest

from apps.analysis.models import Analysis
from apps.jobs.tests.test_jobs import client_with_token
from apps.learning.tests.test_learning import analysis as analysis

pytestmark = pytest.mark.django_db(transaction=True)


def test_endpoint_query_retains_original_indices_links_and_does_not_search_views(
    analysis: Analysis,
) -> None:
    client = client_with_token()
    url = f"/api/v1/analyses/{analysis.pk}/endpoints/"
    original = client.get(url + "?page_size=100").json()["results"]
    before = Analysis.objects.values().get(pk=analysis.pk)
    assert len(original) > 1
    query = "post"
    expected = [
        item
        for item in original
        if query in item["method"].casefold() or query in item["path"].casefold()
    ]
    assert expected
    page = client.get(url, {"q": query, "page_size": "1"}).json()
    gathered: list[dict[str, Any]] = page["results"]
    while page["next"]:
        assert "q=post" in page["next"]
        page = client.get(page["next"]).json()
        gathered += page["results"]
    assert gathered == expected
    view_query = original[0]["view"]
    if isinstance(view_query, dict):
        view_query = view_query["name"]
    assert client.get(url, {"q": view_query}).json()["count"] == 0
    assert client.get(url, {"q": "a" * 200}).status_code == 200
    for query in ("q=" + "a" * 201, "q=get&q=post", "q=x&other=1"):
        assert client.get(url + "?" + query).status_code == 400
    assert Analysis.objects.values().get(pk=analysis.pk) == before
