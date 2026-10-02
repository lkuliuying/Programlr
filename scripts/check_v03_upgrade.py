"""仅在标记的空数据库构造 v0.2 历史，核验 v0.3 增量升级保留原列内容。"""

import hashlib
import io
import json
import os
import sys
import time
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    if os.environ.get("VERIFY_V03_UPGRADE") != "isolated-empty-database":
        raise RuntimeError("升级验收必须明确标记隔离空数据库。")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    import django

    django.setup()
    from django.conf import settings
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.utils import timezone

    if connection.introspection.table_names():
        raise RuntimeError("数据库非空，拒绝执行合成升级。")
    settings.IMPORT_STORAGE_ROOT = "/tmp/v03-upgrade-imports"
    executor = MigrationExecutor(connection)
    old_targets = [
        (app, "0001_initial" if app in {"learning", "labs"} else name)
        for app, name in executor.loader.graph.leaf_nodes()
    ]
    executor.migrate(old_targets)
    historical = executor.loader.project_state(old_targets).apps
    from apps.analysis.graph import build_graph
    from apps.analysis.models import Analysis, AnalysisGraph
    from apps.analysis.parser import analyze
    from apps.analysis.types import Source
    from apps.jobs.models import Job
    from apps.labs.definition import definition
    from apps.labs.models import LabRun
    from apps.projects.models import Project, Snapshot
    from apps.projects.services import execute_import, submit_import

    sources = [
        Source(path.name, path.read_text(encoding="utf-8"))
        for path in sorted((root / "testdata/analysis/drf-static").glob("*.py"))
    ]
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        for source in sources:
            output.writestr(source.file_path, source.content)
    project = Project.objects.create(
        name="v0.2 合成升级历史", idempotency_key=uuid.uuid4()
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
        scope="v03-upgrade-analysis",
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
    example_type = historical.get_model("learning", "TeachingExample")
    exercise_type = historical.get_model("learning", "Exercise")
    attempt_type = historical.get_model("learning", "ExerciseAttempt")
    example = example_type.objects.create(
        version="upgrade-legacy/1", files={}, content_digest="b" * 64
    )
    exercise = exercise_type.objects.create(
        slug="upgrade-legacy",
        version="1",
        answer_version="1",
        kind="flow_order",
        example=example,
        question="合成旧题目",
        hint="合成旧提示",
        options=["request", "response"],
        answer=["request", "response"],
        explanation="合成旧答案说明",
        source_refs=[],
        review_note="仅用于迁移验收",
        content_digest="c" * 64,
    )
    attempt = attempt_type.objects.create(
        exercise=exercise,
        snapshot_id=snapshot.pk,
        analysis_id=analysis.pk,
        endpoint_index=0,
        idempotency_key=uuid.uuid4(),
        request_digest="d" * 64,
        answer=["request", "response"],
        hint_used=True,
        correct=True,
        feedback={
            "expected_answer": exercise.answer,
            "explanation": "旧反馈",
            "source_refs": [],
        },
    )
    lab_job = Job.objects.create(
        kind="lab",
        status="succeeded",
        stage="completed",
        idempotency_key=uuid.uuid4(),
        scope="v03-upgrade-lab",
        expires_at=timezone.now(),
        request_digest="e" * 64,
    )
    old_run = LabRun.objects.create(
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
    # 只选择迁移前存在的列，使新增可空列不掩盖旧列内容的改变。
    with connection.cursor() as cursor:
        columns = {
            table: [
                item.name
                for item in connection.introspection.get_table_description(
                    cursor, table
                )
            ]
            for table in connection.introspection.table_names()
            if table != "django_migrations"
        }

    def dump() -> str:
        values = {}
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            for table, fields in sorted(columns.items()):
                cursor.execute(
                    f"SELECT {','.join(quote(field) for field in fields)} FROM {quote(table)} ORDER BY {quote(fields[0])}"
                )
                values[table] = cursor.fetchall()
        return hashlib.sha256(
            json.dumps(values, sort_keys=True, default=str).encode()
        ).hexdigest()

    before = dump()
    start = time.monotonic()
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    elapsed = time.monotonic() - start
    assert dump() == before, "升级改变了迁移前的列内容"
    from apps.labs.models import SystemLabRun
    from apps.learning.content import load_content
    from apps.learning.models import AttemptReview, ExerciseAttempt, KnowledgeCurriculum
    from rest_framework.test import APIClient

    restored = ExerciseAttempt.objects.get(pk=attempt.pk)
    assert (
        restored.previous_attempt_id is None and restored.hint_used and restored.correct
    )
    assert AttemptReview.objects.count() == 0 and SystemLabRun.objects.count() == 0
    load_content()
    assert KnowledgeCurriculum.objects.count() == 1
    assert dump() != before
    assert ExerciseAttempt.objects.get(pk=attempt.pk).feedback == attempt.feedback
    client = APIClient(HTTP_HOST=settings.APP_AUTHORITY)
    response = client.get(f"/api/v1/exercise-attempts/{attempt.pk}/")
    assert (
        response.status_code == 200 and response.json()["previous_attempt_id"] is None
    )
    response = client.get(f"/api/v1/lab-runs/{old_run.pk}/")
    assert (
        response.status_code == 200
        and response.json()["definition"] == old_run.definition
    )
    print(
        f"v0.2 → v0.3 升级通过：{len(columns)} 张旧表原列摘要一致；旧作答/实验可读取，课程发布成功；迁移 {elapsed:.3f}s。"
    )


if __name__ == "__main__":
    main()
