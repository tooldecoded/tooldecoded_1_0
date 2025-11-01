from django.conf import settings
from django.db import models
from django.utils import timezone


class BackofficeAudit(models.Model):
    ENTITY_COMPONENT = "component"
    ENTITY_PRODUCT = "product"

    ENTITY_CHOICES = (
        (ENTITY_COMPONENT, "Component"),
        (ENTITY_PRODUCT, "Product"),
    )

    id = models.BigAutoField(primary_key=True)
    entity_type = models.CharField(max_length=32, choices=ENTITY_CHOICES)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=32)
    payload_before = models.JSONField(blank=True, null=True)
    payload_after = models.JSONField(blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_management_audit_entries",
    )
    source = models.CharField(max_length=64, default="product_management")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "-created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.entity_id} {self.action}"
