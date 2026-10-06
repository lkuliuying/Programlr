from django.urls import path

from apps.learning.api.knowledge_views import (
    SnapshotKnowledgeCardsView,
    SnapshotKnowledgeHitsView,
)
from apps.learning.api.path_views import (
    AttemptReviewsView,
    CurriculaView,
    CurriculumDetailView,
    LearningPathView,
)
from apps.learning.api.progress_views import (
    CurriculumCardProgressView,
    CurriculumProgressView,
)
from apps.learning.api.views import (
    ExerciseAttemptDetailView,
    ExerciseAttemptsView,
    ExerciseDetailView,
    ExercisesView,
    KnowledgeCardDetailView,
    KnowledgeCardsView,
)

urlpatterns = [
    path(
        "snapshots/<uuid:snapshot_id>/knowledge-cards/",
        SnapshotKnowledgeCardsView.as_view(),
    ),
    path(
        "snapshots/<uuid:snapshot_id>/knowledge-hits/",
        SnapshotKnowledgeHitsView.as_view(),
    ),
    path("knowledge-curricula/", CurriculaView.as_view()),
    path("knowledge-curricula/<uuid:curriculum_id>/", CurriculumDetailView.as_view()),
    path(
        "knowledge-curricula/<uuid:curriculum_id>/progress/",
        CurriculumProgressView.as_view(),
    ),
    path(
        "knowledge-curricula/<uuid:curriculum_id>/progress/<uuid:card_id>/",
        CurriculumCardProgressView.as_view(),
    ),
    path("learning-paths/", LearningPathView.as_view()),
    path("attempt-reviews/", AttemptReviewsView.as_view()),
    path("knowledge-cards/", KnowledgeCardsView.as_view()),
    path("knowledge-cards/<uuid:card_id>/", KnowledgeCardDetailView.as_view()),
    path("exercises/", ExercisesView.as_view()),
    path("exercises/<uuid:exercise_id>/", ExerciseDetailView.as_view()),
    path("exercise-attempts/", ExerciseAttemptsView.as_view()),
    path("exercise-attempts/<uuid:attempt_id>/", ExerciseAttemptDetailView.as_view()),
]
