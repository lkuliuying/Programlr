import json
import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.explanations.configuration import digest
from apps.explanations.context import build_payload, check_preview
from apps.explanations.models import ContextPreview
from apps.explanations.tests.test_adapter import OPTIONS
from apps.explanations.validation import TEMPLATE_VERSION
from apps.learning.models import KnowledgeCard
from apps.learning.tests.test_source_knowledge import TEXT, fixture
from common.errors import ApiProblem

pytestmark = pytest.mark.django_db


def test_preview_includes_only_retained_source_cards_and_versions() -> None:
    _, analysis = fixture()
    ref = {
        "snapshot_id": str(analysis.snapshot_id),
        "file_path": "a.py",
        "start_line": 2,
        "end_line": 4,
    }
    node = {
        "id": str(uuid.uuid4()),
        "name": "selected",
        "kind": "function",
        "source_ref": ref,
        "evidence": [],
    }
    with (
        override_settings(MODEL_OPTIONS=OPTIONS),
        patch(
            "apps.explanations.context.query_graph",
            return_value={"nodes": [node], "edges": [], "truncation_reasons": []},
        ),
        patch(
            "apps.explanations.context.source_content",
            return_value="\n".join(TEXT.splitlines()[1:4]),
        ),
        patch("apps.explanations.services.complete") as model,
    ):
        payload = build_payload(analysis, 0, None)
        assert TEMPLATE_VERSION == "explanation/1.1.0"
        assert {item["slug"] for item in payload["knowledge_cards"]} == {
            "python-context-managers"
        }
        assert all(item["version"] == "1.1.0" for item in payload["knowledge_cards"])
        assert (
            json.loads(payload["messages"][1]["content"])["knowledge_cards"]
            == payload["knowledge_cards"]
        )
        preview = ContextPreview.objects.create(
            analysis=analysis,
            snapshot=analysis.snapshot,
            endpoint_index=0,
            idempotency_key=uuid.uuid4(),
            request_digest="0" * 64,
            payload=payload,
            payload_digest=digest(payload),
        )
        check_preview(preview)
        KnowledgeCard.objects.filter(
            slug="python-context-managers", version="1.1.0"
        ).update(content_digest="f" * 64)
        with pytest.raises(ApiProblem) as stale:
            check_preview(preview)
        assert stale.value.machine_code == "CONSENT_STALE"
        model.assert_not_called()


def test_old_preview_defaults_and_exclusion_do_not_inject_unrelated_cards() -> None:
    from apps.explanations.api.serializers import ContextPreviewSerializer
    from apps.learning.knowledge import preview_cards

    _, analysis = fixture()
    assert preview_cards(analysis, []) == []
    other = {
        "snapshot_id": str(analysis.snapshot_id),
        "file_path": "a.py",
        "start_line": 5,
        "end_line": 6,
    }
    assert {item["slug"] for item in preview_cards(analysis, [other])} == {
        "python-generators"
    }
    assert preview_cards(analysis, [other], endpoint_index=0) == []
    broad = dict(other, start_line=1)
    assert {
        item["slug"] for item in preview_cards(analysis, [broad], endpoint_index=0)
    } == {"python-context-managers"}
    data = {
        "id": uuid.uuid4(),
        "analysis_id": analysis.pk,
        "snapshot_id": analysis.snapshot_id,
        "endpoint_index": 0,
        "payload_digest": "0" * 64,
        "configuration": {
            "base_url": "https://model-test.invalid/v1",
            "model": "test-model",
        },
        "template_version": "explanation/1.0.0",
        "messages": [],
        "snippets": [],
        "excluded_snippets": [],
        "nodes": [],
        "omissions": [],
        "context_bytes": 0,
        "created_at": analysis.created_at,
    }
    assert ContextPreviewSerializer(data).data["knowledge_cards"] == []
