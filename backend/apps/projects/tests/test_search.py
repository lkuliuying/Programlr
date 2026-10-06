import uuid

import pytest

from apps.jobs.models import Job
from apps.jobs.tests.test_jobs import client_with_token
from apps.projects.models import Project
from apps.projects.services import create_project

pytestmark = pytest.mark.django_db(transaction=True)


def test_project_query_filters_before_pagination_preserves_links_and_no_writes() -> (
    None
):
    for name in ("Other", "Alpha %", "alpha 中文"):
        create_project(uuid.uuid4(), name)
    client = client_with_token()
    page = client.get("/api/v1/projects/", {"q": "ALPHA", "page_size": "1"}).json()
    assert page["count"] == 2 and "q=ALPHA" in page["next"]
    assert client.get(page["next"]).json()["results"][0]["name"] == "Alpha %"
    assert client.get("/api/v1/projects/?q=%25").json()["count"] == 1
    assert client.get("/api/v1/projects/?q=missing").json()["results"] == []
    assert client.get("/api/v1/projects/?q=").json()["count"] == 3
    assert client.get("/api/v1/projects/", {"q": "中" * 200}).status_code == 200
    for query in ("q=" + "a" * 201, "q=alpha&q=other", "q=x&unknown=1"):
        assert client.get("/api/v1/projects/?" + query).status_code == 400
    assert Project.objects.count() == 3 and Job.objects.count() == 0
