from rest_framework.viewsets import ModelViewSet

from serializers import TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
