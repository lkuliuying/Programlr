import uuid
from typing import TYPE_CHECKING

from django.db import transaction
from django.shortcuts import get_object_or_404

from common.errors import ApiProblem

if TYPE_CHECKING:
    from apps.projects.models import Project, Snapshot


def require_project_available(project: "Project") -> None:
    if project.deletion_request_id is not None:
        raise ApiProblem(410, "RESOURCE_DELETING", "项目正在永久清理，不能读取或操作。")


def require_snapshot_available(snapshot: "Snapshot") -> None:
    require_project_available(snapshot.project)
    if snapshot.deletion_request_id is not None:
        raise ApiProblem(410, "RESOURCE_DELETING", "快照正在永久清理，不能读取或操作。")


def lock_project(project_id: uuid.UUID) -> "Project":
    from apps.projects.models import Project

    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("资源行锁必须在事务中获取。")
    project = get_object_or_404(Project.objects.select_for_update(), pk=project_id)
    require_project_available(project)
    return project


def lock_snapshot(snapshot_id: uuid.UUID) -> "Snapshot":
    from apps.projects.models import Snapshot

    initial = get_object_or_404(Snapshot, pk=snapshot_id)
    lock_project(initial.project_id)
    snapshot = get_object_or_404(
        Snapshot.objects.select_for_update().select_related("project"), pk=snapshot_id
    )
    require_snapshot_available(snapshot)
    return snapshot
