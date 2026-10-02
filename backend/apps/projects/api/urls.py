from django.urls import path

from apps.projects.api.views import (
    ImportsView,
    ProjectDetailView,
    ProjectsView,
    SnapshotDetailView,
    SnapshotsView,
    SourceContentView,
    SourceFilesView,
)

urlpatterns = [
    path("projects/", ProjectsView.as_view()),
    path("projects/<uuid:project_id>/", ProjectDetailView.as_view()),
    path("projects/<uuid:project_id>/imports/", ImportsView.as_view()),
    path("projects/<uuid:project_id>/snapshots/", SnapshotsView.as_view()),
    path("snapshots/<uuid:snapshot_id>/", SnapshotDetailView.as_view()),
    path("snapshots/<uuid:snapshot_id>/files/", SourceFilesView.as_view()),
    path(
        "snapshots/<uuid:snapshot_id>/files/<uuid:file_id>/content/",
        SourceContentView.as_view(),
    ),
]
