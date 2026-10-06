from django.urls import path

from apps.analysis.api.comparison_views import (
    ComparisonDetailView,
    ComparisonFileDetailView,
    ComparisonFilesView,
    ProjectComparisonsView,
)
from apps.analysis.api.impact_views import AnalysisImpactView, ComparisonImpactView
from apps.analysis.api.review_views import RelationReviewsView
from apps.analysis.api.scan_views import (
    EndpointRelationsView,
    SourceScanDetailView,
    SourceScansView,
)
from apps.analysis.api.views import (
    AnalysesView,
    AnalysisDetailView,
    DiagnosticsView,
    EndpointsView,
    GraphView,
)

urlpatterns = [
    path("snapshots/<uuid:snapshot_id>/source-scans/", SourceScansView.as_view()),
    path("source-scans/<uuid:scan_id>/", SourceScanDetailView.as_view()),
    path(
        "analyses/<uuid:analysis_id>/endpoint-relations/",
        EndpointRelationsView.as_view(),
    ),
    path("analyses/<uuid:analysis_id>/impact/", AnalysisImpactView.as_view()),
    path(
        "snapshot-comparisons/<uuid:comparison_id>/impact/",
        ComparisonImpactView.as_view(),
    ),
    path(
        "projects/<uuid:project_id>/snapshot-comparisons/",
        ProjectComparisonsView.as_view(),
    ),
    path("snapshot-comparisons/<uuid:comparison_id>/", ComparisonDetailView.as_view()),
    path(
        "snapshot-comparisons/<uuid:comparison_id>/files/",
        ComparisonFilesView.as_view(),
    ),
    path(
        "snapshot-comparisons/<uuid:comparison_id>/files/<uuid:change_id>/",
        ComparisonFileDetailView.as_view(),
    ),
    path("snapshots/<uuid:snapshot_id>/analyses/", AnalysesView.as_view()),
    path("analyses/<uuid:analysis_id>/", AnalysisDetailView.as_view()),
    path("analyses/<uuid:analysis_id>/endpoints/", EndpointsView.as_view()),
    path("analyses/<uuid:analysis_id>/diagnostics/", DiagnosticsView.as_view()),
    path("analyses/<uuid:analysis_id>/graph/", GraphView.as_view()),
    path(
        "analyses/<uuid:analysis_id>/relation-reviews/", RelationReviewsView.as_view()
    ),
]
