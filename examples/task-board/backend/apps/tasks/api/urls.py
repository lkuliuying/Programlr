from django.urls import path

from apps.tasks.api.views import TaskListCreateView

urlpatterns = [path("tasks/", TaskListCreateView.as_view(), name="tasks")]
