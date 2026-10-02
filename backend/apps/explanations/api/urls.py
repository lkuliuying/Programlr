from django.urls import path

from apps.explanations.api.views import (
    ContextConsentsView,
    ContextPreviewDetailView,
    ContextPreviewsView,
    ExplanationDetailView,
    ExplanationsView,
)

urlpatterns = [
    path("context-previews/", ContextPreviewsView.as_view()),
    path("context-previews/<uuid:preview_id>/", ContextPreviewDetailView.as_view()),
    path("context-previews/<uuid:preview_id>/consents/", ContextConsentsView.as_view()),
    path("explanations/", ExplanationsView.as_view()),
    path("explanations/<uuid:explanation_id>/", ExplanationDetailView.as_view()),
]
