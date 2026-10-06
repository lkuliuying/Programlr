"""项目管理只读投影，技术标签仅来自快照文件和已发布扫描事实。"""

import uuid
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any

from django.db.models import Case, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_datetime

from apps.analysis.models import SnapshotPreparation
from apps.jobs.models import OperationLog
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}
PACKAGES = {
    "django": "Django",
    "djangorestframework": "DRF",
    "rest_framework": "DRF",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "sqlalchemy": "SQLAlchemy",
    "celery": "Celery",
    "redis": "Redis",
    "pytest": "pytest",
    "requests": "Requests",
    "httpx": "HTTPX",
    "pydantic": "Pydantic",
}


def preparations(snapshots: list[Snapshot]) -> dict[uuid.UUID, SnapshotPreparation]:
    return {
        item.snapshot_id: item
        for item in SnapshotPreparation.objects.filter(
            snapshot__in=snapshots
        ).select_related("scan_job", "analysis_job", "analysis", "source_scan")
    }


def preparation_values(preparation: SnapshotPreparation | None) -> dict[str, Any]:
    status = preparation.status if preparation else "pending"
    if preparation and any(
        job and job.status == "failed"
        for job in (preparation.scan_job, preparation.analysis_job)
    ):
        status = "failed"
    return {
        "preparation_status": status,
        **{
            name: str(value) if value else None
            for name, value in {
                "source_scan_id": preparation.source_scan_id if preparation else None,
                "scan_job_id": preparation.scan_job_id if preparation else None,
                "analysis_job_id": preparation.analysis_job_id if preparation else None,
                "analysis_id": preparation.analysis_id if preparation else None,
            }.items()
        },
    }


def root_summary(
    preparation: SnapshotPreparation | None,
) -> tuple[int | None, str | None]:
    if not preparation or not preparation.source_scan:
        return None, None
    roots = preparation.source_scan.result.get("roots", {})
    candidates = roots.get("candidates")
    count = len(candidates) if isinstance(candidates, list) else None
    path = (
        preparation.analysis.root_urlconf
        if preparation.analysis
        else roots.get("selected_root")
    )
    return count, path if isinstance(path, str) else None


def project_summaries(query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    latest = Snapshot.objects.filter(
        project_id=OuterRef("pk"), deletion_request_id__isnull=True
    ).order_by("-created_at", "-id")
    owners = list(
        Project.objects.filter(
            deletion_request_id__isnull=True, name__icontains=query
        ).annotate(latest_id=Subquery(latest.values("id")[:1]))
    )
    snapshots = list(
        Snapshot.objects.filter(pk__in=[owner.latest_id for owner in owners])
    )
    by_id = {snapshot.pk: snapshot for snapshot in snapshots}
    prepared = preparations(snapshots)
    counts = Counter(
        Snapshot.objects.filter(
            project__in=owners, deletion_request_id__isnull=True
        ).values_list("project_id", flat=True)
    )
    technologies: dict[uuid.UUID, set[tuple[str, str]]] = defaultdict(set)
    for snapshot_id, file_path in (
        SourceFile.objects.filter(snapshot__in=snapshots)
        .values_list("snapshot_id", "file_path")
        .iterator()
    ):
        name = LANGUAGES.get(PurePosixPath(file_path).suffix.lower())
        if name:
            technologies[snapshot_id].add((name, "language"))
    for identifier, preparation in prepared.items():
        if not preparation.source_scan:
            continue
        knowledge = preparation.source_scan.result.get("knowledge", {})
        for declaration in knowledge.get("declarations", []):
            name = PACKAGES.get(declaration.get("distribution"))
            if name:
                technologies[identifier].add((name, "declaration"))
        identities: dict[str, set[tuple[str | None, str | None]]] = defaultdict(set)
        for package in knowledge.get("packages", []):
            identities[package.get("name", "")].add(
                (package.get("kind"), package.get("distribution"))
            )
        for package in knowledge.get("packages", []):
            identity = identities[package.get("name", "")]
            name = PACKAGES.get(package.get("distribution"))
            # 同名本地模块或冲突身份不能被呈现为框架使用证据。
            if (
                name
                and len(identity) == 1
                and package.get("kind") == "third_party"
                and (package.get("usage_refs") or package.get("source_refs"))
            ):
                technologies[identifier].add((name, "usage"))
    results = []
    for owner in owners:
        snapshot = by_id.get(owner.latest_id)
        root_count, root_path = root_summary(
            prepared.get(snapshot.pk) if snapshot else None
        )
        results.append(
            {
                "project": owner,
                "snapshot_count": counts[owner.pk],
                "latest_snapshot": snapshot,
                "last_imported_at": snapshot.created_at if snapshot else None,
                "technologies": [
                    {"name": name, "evidence_kind": evidence}
                    for name, evidence in sorted(technologies[snapshot.pk])
                ]
                if snapshot
                else [],
                "root_count": root_count,
                "root_path": root_path,
            }
        )
    return results, {
        "preparation_fields": {
            snapshot.pk: preparation_values(prepared.get(snapshot.pk))
            for snapshot in snapshots
        }
    }


def activity() -> tuple[dict[str, Any], dict[str, Any]]:
    available = Snapshot.objects.filter(
        deletion_request_id__isnull=True, project__deletion_request_id__isnull=True
    ).annotate(
        activity_at=Coalesce(
            "preparation__analysis_job__updated_at",
            "preparation__scan_job__updated_at",
            "job__updated_at",
        )
    )
    selected = list(
        available.filter(
            Q(
                preparation__status__in=[
                    "pending",
                    "scanning",
                    "needs_root",
                    "analyzing",
                    "failed",
                ]
            )
            | Q(preparation__scan_job__status="failed")
            | Q(preparation__analysis_job__status="failed")
            | Q(preparation__isnull=True)
        )
        .select_related("project", "job")
        .order_by("-activity_at", "-id")[:5]
    )
    recent = list(
        available.filter(preparation__status__in=["ready", "no_root"])
        .exclude(preparation__scan_job__status="failed")
        .exclude(preparation__analysis_job__status="failed")
        .select_related("project", "job")
        .order_by("-activity_at", "-id")[:5]
    )
    prepared = preparations([*selected, *recent])
    importing = list(
        ImportRequest.objects.filter(
            project__deletion_request_id__isnull=True,
            job__status__in=["queued", "running", "failed"],
            job__result_deleted_at__isnull=True,
        )
        .select_related("project", "job")
        .order_by("-job__updated_at", "-job_id")[:5]
    )
    items: list[dict[str, Any]] = []
    for record in importing:
        items.append(
            {
                "project": record.project,
                "snapshot": None,
                "status": "failed" if record.job.status == "failed" else "importing",
                "root_count": None,
                "endpoint_count": None,
                "stages": [{"kind": "import", "job": record.job}],
                "sort_at": record.job.updated_at,
            }
        )
    for snapshot in [*selected, *recent]:
        preparation = prepared.get(snapshot.pk)
        status = preparation_values(preparation)["preparation_status"]
        root_count, _ = root_summary(preparation)
        stages: list[dict[str, Any]] = [{"kind": "import", "job": snapshot.job}]
        if preparation:
            for kind, job in (
                ("source_scan", preparation.scan_job),
                ("analysis", preparation.analysis_job),
            ):
                if job:
                    stages.append({"kind": kind, "job": job})
        items.append(
            {
                "project": snapshot.project,
                "snapshot": snapshot,
                "status": status,
                "root_count": root_count,
                "endpoint_count": len(preparation.analysis.endpoints)
                if preparation and preparation.analysis
                else None,
                "stages": stages,
                "sort_at": stages[-1]["job"].updated_at,
            }
        )
    events: dict[uuid.UUID, list[dict[str, Any]]] = {}
    jobs = [stage["job"].pk for item in items for stage in item["stages"]]
    # 完成后的幂等重放只记录本次响应，不能遮住原任务的真实执行阶段。
    logs = (
        OperationLog.objects.filter(job_id__in=jobs)
        .annotate(
            replay_priority=Case(
                When(result="replayed", then=Value(1)), default=Value(0)
            )
        )
        .order_by("job_id", "replay_priority", "created_at", "id")
    )
    for identifier, values in logs.values_list("job_id", "events"):
        if identifier in events or not isinstance(values, list):
            continue
        events[identifier] = [
            {
                "at": parse_datetime(value["at"]),
                "result": value["result"],
                "stage": str(value.get("stage", "")),
                "error_code": str(value.get("error_code", "")),
            }
            for value in values
            if isinstance(value, dict)
            and isinstance(value.get("at"), str)
            and parse_datetime(value["at"]) is not None
            and isinstance(value.get("result"), str)
        ]
    for item in items:
        for stage in item["stages"]:
            stage["events"] = events.get(stage["job"].pk, [])
    items.sort(key=lambda item: item["sort_at"], reverse=True)
    return {
        "active": [
            item for item in items if item["status"] not in {"ready", "no_root"}
        ][:5],
        "recent": [item for item in items if item["status"] in {"ready", "no_root"}][
            :5
        ],
    }, {
        "preparation_fields": {
            identifier: preparation_values(value)
            for identifier, value in prepared.items()
        }
    }
