"""从现有请求与资源状态读取恢复资格，不创建任务或重新取得执行授权。"""

from django.db.models import Case, CharField, Exists, OuterRef, Q, QuerySet, Value, When

from apps.analysis.models import AnalysisRequest
from apps.explanations.models import ExplanationRequest
from apps.jobs.models import DeletionRequest, OperationLog
from apps.projects.models import ImportRequest, Project, Snapshot, SourceFile
from common.retirement import RETIRED_JOB_KINDS

RETRY_ACTIONS = (
    "none",
    "direct",
    "upload_zip",
    "select_folder",
    "reconfirm_explanation",
    "continue_cleanup",
)


def annotate_operation_capabilities(
    logs: QuerySet[OperationLog],
) -> QuerySet[OperationLog]:
    available = {
        "deletion_request_id__isnull": True,
        "project__deletion_request_id__isnull": True,
    }
    snapshots = Snapshot.objects.filter(pk=OuterRef("job__snapshot_id"), **available)
    imports = ImportRequest.objects.filter(
        job_id=OuterRef("job_id"),
        project__deletion_request_id__isnull=True,
    )
    roots = SourceFile.objects.filter(
        snapshot_id=OuterRef("snapshot_id"),
        file_path=OuterRef("root_urlconf"),
    )
    analyses = (
        AnalysisRequest.objects.filter(
            job_id=OuterRef("job_id"),
            snapshot__deletion_request_id__isnull=True,
            snapshot__project__deletion_request_id__isnull=True,
        )
        .annotate(root_available=Exists(roots))
        .filter(root_available=True)
    )
    explanations = ExplanationRequest.objects.filter(
        job_id=OuterRef("job_id"),
        consent__preview__snapshot__deletion_request_id__isnull=True,
        consent__preview__snapshot__project__deletion_request_id__isnull=True,
    )
    cleanup = DeletionRequest.objects.filter(
        current_job_id=OuterRef("job_id"),
        completed_at__isnull=True,
    )
    deleted = DeletionRequest.objects.filter(
        Q(target_type="snapshot", target_id=OuterRef("snapshot_id"))
        | Q(target_type="project", target_id=OuterRef("project_id")),
        completed_at__isnull=False,
    )
    logs = logs.annotate(
        _snapshot_available=Exists(snapshots),
        _import_available=Exists(imports),
        _analysis_available=Exists(analyses),
        _explanation_available=Exists(explanations),
        _cleanup_available=Exists(cleanup),
        _target_deleted=Exists(deleted),
        project_available=Exists(
            Project.objects.filter(
                pk=OuterRef("project_id"),
                deletion_request_id__isnull=True,
            )
        ),
    )
    return logs.annotate(
        retry_action=Case(
            When(
                ~Q(result="failed") | ~Q(job__status="failed") | Q(job__isnull=True),
                then=Value("none"),
            ),
            When(
                Q(job__kind__in=RETIRED_JOB_KINDS)
                | Q(job__result_deleted_at__isnull=False)
                | Q(_target_deleted=True),
                then=Value("none"),
            ),
            When(
                job__kind="delete",
                _cleanup_available=True,
                then=Value("continue_cleanup"),
            ),
            When(
                job__kind="import",
                _import_available=True,
                job__source_kind="folder",
                then=Value("select_folder"),
            ),
            When(job__kind="import", _import_available=True, then=Value("upload_zip")),
            When(job__kind="analysis", _analysis_available=True, then=Value("direct")),
            When(
                job__kind="source_scan", _snapshot_available=True, then=Value("direct")
            ),
            When(
                job__kind="explanation",
                _explanation_available=True,
                then=Value("reconfirm_explanation"),
            ),
            default=Value("none"),
            output_field=CharField(),
        )
    )
