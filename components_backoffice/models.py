from django.conf import settings
from django.db import models
from django.utils import timezone


class ComponentAudit(models.Model):
    """Audit log for component field changes made via backoffice.

    Stored in this app only to avoid touching existing schemas.
    """
    id = models.AutoField(primary_key=True)
    component_id = models.UUIDField()
    field = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=50, default="inline")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["component_id", "-created_at"]),
            models.Index(fields=["field"]),
        ]


