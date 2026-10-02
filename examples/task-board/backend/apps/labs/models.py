import uuid

from django.db import models


class LabSession(models.Model):
    objects: models.Manager["LabSession"] = models.Manager()
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    closed = models.BooleanField(default=False)
    expires_at = models.DateTimeField(db_index=True)
    deleted_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
