from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from product_management.models import BackofficeAudit
from toolanalysis.models import Components, Products


ENTITY_MODEL_MAP = {
    BackofficeAudit.ENTITY_COMPONENT: Components,
    BackofficeAudit.ENTITY_PRODUCT: Products,
}


def _serialize_value(field, value):
    if value is None:
        return None
    if hasattr(field, "remote_field") and getattr(field.remote_field, "model", None):
        if not value:
            return None
        identifier = getattr(value, "id", None)
        return str(identifier or value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def snapshot_instance(instance) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    m2m: Dict[str, Iterable[str]] = {}

    for field in instance._meta.concrete_fields:
        if field.attname == "id" or field.primary_key:
            continue
        if getattr(field, "remote_field", None):
            value = getattr(instance, field.name)
        else:
            attr_name = getattr(field, "attname", field.name)
            value = getattr(instance, attr_name)
        fields[field.name] = _serialize_value(field, value)

    for field in instance._meta.many_to_many:
        related_ids = list(
            getattr(instance, field.name).values_list("id", flat=True)
        )
        m2m[field.name] = [str(pk) for pk in related_ids]

    return {"fields": fields, "m2m": m2m}


def record_audit_entry(entity_type: str, instance, action: str, *, user=None, before=None) -> None:
    BackofficeAudit.objects.create(
        entity_type=entity_type,
        entity_id=getattr(instance, "id"),
        action=action,
        payload_before=before,
        payload_after=snapshot_instance(instance),
        user=user,
    )


@transaction.atomic
def undo_last_change(entity_type: str, entity_id, *, user=None) -> bool:
    if entity_type not in ENTITY_MODEL_MAP:
        raise ValidationError({"entity_type": "Unsupported entity type."})

    audit = (
        BackofficeAudit.objects.filter(entity_type=entity_type, entity_id=entity_id)
        .order_by("-created_at")
        .first()
    )
    if not audit:
        raise ValidationError("No audit history available to undo.")

    model = ENTITY_MODEL_MAP[entity_type]

    if audit.action == "create":
        try:
            instance = model.objects.get(id=entity_id)
        except model.DoesNotExist as exc:
            raise ValidationError("Record already removed; nothing to undo.") from exc
        snapshot = snapshot_instance(instance)
        instance.delete()
        BackofficeAudit.objects.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action="undo_create",
            payload_before=snapshot,
            payload_after=None,
            user=user,
        )
        return True

    raise ValidationError("Undo is only supported for create actions at this time.")

