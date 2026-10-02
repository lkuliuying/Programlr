"""只在隔离验收数据库构造 v0.1 历史并验证增量升级，禁止用于已有实例。"""

import hashlib
import io
import json
import os
import resource
import sys
import time
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    if os.environ.get("VERIFY_V02_UPGRADE") != "isolated-empty-database":
        raise RuntimeError("此脚本只接受明确标记的隔离空数据库。")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    import django

    django.setup()
    from django.conf import settings

    settings.IMPORT_STORAGE_ROOT = "/tmp/v02-upgrade-imports"
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.utils import timezone

    if connection.introspection.table_names():
        raise RuntimeError("升级验收要求空数据库，拒绝覆盖任何已有表。")
    executor = MigrationExecutor(connection)
    old_targets = [
        (app, "0003_analysis_frontend" if app == "analysis" else name)
        for app, name in executor.loader.graph.leaf_nodes()
    ]
    # 旧迁移名称从图核对，避免误写名称导致假升级验证。
    old_name = next(
        name
        for app, name in executor.loader.disk_migrations
        if app == "analysis" and name.startswith("0003_")
    )
    old_targets = [
        (app, old_name if app == "analysis" else name) for app, name in old_targets
    ]
    executor.migrate(old_targets)
    from apps.analysis.graph import build_graph
    from apps.analysis.models import Analysis, AnalysisGraph
    from apps.analysis.parser import analyze
    from apps.analysis.types import Source
    from apps.explanations.models import ContextPreview, Explanation
    from apps.explanations.validation import TEMPLATE_VERSION
    from apps.jobs.models import Job
    from apps.projects.models import Project, Snapshot
    from apps.projects.services import execute_import, submit_import

    root = Path(__file__).resolve().parents[1]
    source_root = root / "testdata/analysis/drf-static"
    sources = [
        Source(path.name, path.read_text(encoding="utf-8"))
        for path in sorted(source_root.glob("*.py"))
    ]
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as target:
        for source in sources:
            target.writestr(source.file_path, source.content)
    project = Project.objects.create(
        name="v0.1 升级验收历史", idempotency_key=uuid.uuid4()
    )
    with patch("apps.jobs.services.app.send_task"):
        job = submit_import(
            project,
            uuid.uuid4(),
            SimpleUploadedFile("upgrade.zip", archive.getvalue(), "application/zip"),
        )[0]
    execute_import(str(job.pk))
    snapshot = Snapshot.objects.get(job=job)
    data = analyze(str(snapshot.pk), sources, "root_urls.py")
    analysis_job = Job.objects.create(
        kind="analysis",
        status="succeeded",
        stage="completed",
        snapshot_id=snapshot.pk,
        idempotency_key=uuid.uuid4(),
        scope="upgrade-analysis",
        expires_at=timezone.now(),
        request_digest="a" * 64,
    )
    analysis = Analysis.objects.create(
        job=analysis_job,
        snapshot=snapshot,
        root_urlconf="root_urls.py",
        rule_version="python-drf/1.0.0",
        coverage=data["coverage"],
        endpoints=data["endpoints"],
        diagnostics=data["diagnostics"],
        frontend=None,
    )
    graph = build_graph(analysis.pk, data)
    AnalysisGraph.objects.create(
        analysis=analysis,
        graph_version="analysis-graph/1.0.0",
        nodes=graph["nodes"],
        edges=graph["edges"],
    )
    ref = {
        "snapshot_id": str(snapshot.pk),
        "file_path": "models.py",
        "start_line": 1,
        "end_line": 1,
    }
    text = sources[
        next(i for i, source in enumerate(sources) if source.file_path == "models.py")
    ].content.splitlines(keepends=True)[0]
    preview = ContextPreview.objects.create(
        analysis=analysis,
        snapshot=snapshot,
        endpoint_index=0,
        idempotency_key=uuid.uuid4(),
        request_digest="a" * 64,
        payload={
            "template_version": TEMPLATE_VERSION,
            "snippets": [
                {
                    "id": "legacy",
                    "source_ref": ref,
                    "content": text,
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                }
            ],
        },
        payload_digest="a" * 64,
    )
    explanation_job = Job.objects.create(
        kind="explanation",
        status="succeeded",
        stage="completed",
        snapshot_id=snapshot.pk,
        idempotency_key=uuid.uuid4(),
        scope="upgrade-explanation",
        expires_at=timezone.now(),
        request_digest="b" * 64,
    )
    content = {
        name: [{"kind": "source_fact", "text": "合成旧讲解", "source_refs": [ref]}]
        for name in ("purpose", "evidence", "mechanism", "knowledge", "verification")
    }
    explanation = Explanation.objects.create(
        job=explanation_job, preview=preview, content=content, model="synthetic-upgrade"
    )
    from apps.labs.definition import definition
    from apps.labs.models import LabRun
    from apps.learning.content import load_content
    from apps.learning.models import Exercise, ExerciseAttempt

    load_content()
    exercise = Exercise.objects.first()
    assert exercise is not None
    ExerciseAttempt.objects.create(
        exercise=exercise,
        snapshot=snapshot,
        analysis=analysis,
        endpoint_index=0,
        idempotency_key=uuid.uuid4(),
        request_digest="c" * 64,
        answer={},
        hint_used=False,
        correct=False,
        feedback={
            "expected_answer": exercise.answer,
            "explanation": exercise.explanation,
            "source_refs": [ref],
        },
    )
    lab_job = Job.objects.create(
        kind="lab",
        status="succeeded",
        stage="completed",
        idempotency_key=uuid.uuid4(),
        scope="upgrade-lab",
        expires_at=timezone.now(),
        request_digest="d" * 64,
    )
    LabRun.objects.create(
        job=lab_job,
        analysis=analysis,
        endpoint_index=0,
        definition=definition(analysis, 0),
        predictions={
            case: {
                "status": 201 if case == "normal" else 400,
                "writes": int(case == "normal"),
            }
            for case in ("normal", "missing", "empty", "whitespace")
        },
        observations=[],
        cleanup={"status": "succeeded", "observation": None, "error_code": None},
    )

    def dump() -> str:
        from django.apps import apps

        values = {
            model._meta.label: list(model._default_manager.order_by("pk").values())
            for model in apps.get_models()
            if model._meta.app_label
            in {"jobs", "projects", "analysis", "explanations", "learning", "labs"}
            and model._meta.model_name
            not in {
                "relationreview",
                "relationreviewstate",
                "snapshotcomparison",
                "snapshotcomparisonrequest",
            }
        }
        return hashlib.sha256(
            json.dumps(values, sort_keys=True, default=str).encode()
        ).hexdigest()

    before = dump()
    started = time.monotonic()
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    assert dump() == before
    from apps.analysis.diffs.services import execute_comparison, submit_comparison
    from apps.analysis.models import RelationReview, SnapshotComparison
    from apps.analysis.services import read_graph
    from rest_framework.test import APIClient

    assert read_graph(analysis)[1] == "analysis-graph/1.0.0"
    client = APIClient()
    for path in (
        f"/api/v1/snapshots/{snapshot.pk}/",
        f"/api/v1/analyses/{analysis.pk}/",
        f"/api/v1/analyses/{analysis.pk}/graph/",
        f"/api/v1/explanations/{explanation.pk}/",
        "/api/v1/exercise-attempts/",
        "/api/v1/lab-runs/",
    ):
        assert client.get(path, HTTP_HOST="127.0.0.1:5173").status_code == 200, path
    with patch("apps.jobs.services.app.send_task"):
        compared = submit_comparison(
            project, uuid.uuid4(), snapshot, snapshot, analysis, analysis
        )[0]
    execute_comparison(str(compared.pk))
    result = SnapshotComparison.objects.get(request__job=compared)
    assert (
        result.data["comparability"] == "comparable"
        and result.data["evidence"][0]["references"][0]["applicability"] == "unchanged"
    )
    assert RelationReview.objects.count() == 0
    print(
        json.dumps(
            {
                "upgrade": "passed",
                "old_records_unchanged": True,
                "legacy_graph_readable": True,
                "old_history_readable": True,
                "files": len(sources),
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "process_peak_rss_kib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
