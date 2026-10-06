from django.urls import path

from apps.jobs.api.operation_views import (
    HistoricalOperationLogsView,
    OperationExportView,
    OperationLogDetailView,
    OperationLogsView,
    OperationStatisticsView,
    RelatedOperationLogsView,
)
from apps.jobs.cleanup_api import (
    ProjectDeletionPreviewView,
    SnapshotDeletionPreviewView,
)

urlpatterns = [
    path("operation-logs/", OperationLogsView.as_view()),
    path("operation-logs/statistics/", OperationStatisticsView.as_view()),
    path("operation-logs/export/", OperationExportView.as_view()),
    path("operation-logs/<uuid:log_id>/", OperationLogDetailView.as_view()),
    path("operation-logs/<uuid:log_id>/related/", RelatedOperationLogsView.as_view()),
    path(
        "operation-logs/<uuid:log_id>/history/", HistoricalOperationLogsView.as_view()
    ),
    path(
        "projects/<uuid:project_id>/deletion-preview/",
        ProjectDeletionPreviewView.as_view(),
    ),
    path(
        "snapshots/<uuid:snapshot_id>/deletion-preview/",
        SnapshotDeletionPreviewView.as_view(),
    ),
]
