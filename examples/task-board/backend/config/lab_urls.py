from django.urls import include, path

from config.urls import handler404, handler500
from config.urls import urlpatterns as public_patterns

__all__ = ["handler404", "handler500", "urlpatterns"]
urlpatterns = [*public_patterns, path("internal/labs/", include("apps.labs.views"))]
