from django.urls import path

from apps.labs.api.system_views import (
    SubmitSystemRunView,
    SystemLabDetailView,
    SystemLabsView,
    SystemRunDetailView,
    SystemRunsView,
)
from apps.labs.api.views import (
    LabDetailView,
    LabsView,
    RunDetailView,
    RunsView,
    SubmitRunView,
)

urlpatterns = [
    path("system-labs/", SystemLabsView.as_view()),
    path("system-labs/<slug:lab_id>/", SystemLabDetailView.as_view()),
    path("system-labs/<slug:lab_id>/runs/", SubmitSystemRunView.as_view()),
    path("system-lab-runs/", SystemRunsView.as_view()),
    path("system-lab-runs/<uuid:run_id>/", SystemRunDetailView.as_view()),
    path("labs/", LabsView.as_view()),
    path("labs/<slug:lab_id>/", LabDetailView.as_view()),
    path("labs/<slug:lab_id>/runs/", SubmitRunView.as_view()),
    path("lab-runs/", RunsView.as_view()),
    path("lab-runs/<uuid:run_id>/", RunDetailView.as_view()),
]
