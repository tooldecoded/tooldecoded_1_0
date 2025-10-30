from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from components_backoffice.models import ComponentAudit
from toolanalysis.models import Components


def _ensure_feature_enabled():
    if not getattr(settings, "ENABLE_COMPONENTS_BACKOFFICE", False):
        raise Http404()


def _rate_limit_key(user_id: int) -> str:
    return f"comp_backoffice_inline_rps:{user_id}"


def _rate_limit(user_id: int) -> bool:
    """Simple fixed-window rate limiter based on settings.COMP_BACKOFFICE_INLINE_RPS per second.

    Returns True if allowed, False if limited.
    """
    max_rps = int(getattr(settings, "COMP_BACKOFFICE_INLINE_RPS", 5))
    now_bucket = int(timezone.now().timestamp())
    key = f"{_rate_limit_key(user_id)}:{now_bucket}"
    try:
        with transaction.atomic():
            current = cache.get(key)
            if current is None:
                cache.set(key, 1, timeout=2)
                return True
            if current >= max_rps:
                return False
            cache.incr(key)
            return True
    except Exception:
        # On cache error, fail open rather than block edits
        return True


# Whitelist of fields editable via inline endpoint and their validators/casters
def _cast_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y", "on"}:
            return True
        if v in {"false", "0", "no", "n", "off"}:
            return False
    raise ValueError("Invalid boolean value")


def _cast_decimal_positive(value):
    if value in ("", None):
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid decimal value")
    if d < 0:
        raise ValueError("Must be >= 0")
    return d


def _cast_int_nonnegative(value):
    try:
        iv = int(value)
    except (TypeError, ValueError):
        raise ValueError("Invalid integer value")
    if iv < 0:
        raise ValueError("Must be >= 0")
    return iv


INLINE_EDIT_WHITELIST = {
    "name": str,
    "is_featured": _cast_bool,
    "standalone_price": _cast_decimal_positive,
    "showcase_priority": _cast_int_nonnegative,
}


@csrf_protect
def component_inline_update_view(request, component_id):
    _ensure_feature_enabled()
    # Superuser-only access
    if not getattr(request.user, "is_authenticated", False) or not getattr(request.user, "is_superuser", False):
        raise Http404()
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if not _rate_limit(request.user.id):
        return JsonResponse({"error": "Rate limit exceeded"}, status=429)

    try:
        payload = request.POST or {}
        # Allow JSON too if sent as application/json
        if request.content_type and "application/json" in request.content_type.lower():
            import json
            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    # Contract: exactly two keys: field and value
    allowed_keys = {"field", "value"}
    if not isinstance(payload, dict) or set(payload.keys()) - allowed_keys or not allowed_keys.issubset(set(payload.keys())):
        return JsonResponse({"error": "Payload must include exactly 'field' and 'value'"}, status=400)

    field = payload.get("field")
    value = payload.get("value")

    if field not in INLINE_EDIT_WHITELIST:
        return JsonResponse({"error": "Field not editable"}, status=400)

    caster = INLINE_EDIT_WHITELIST[field]
    try:
        cast_value = caster(value)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    # Load component
    try:
        component = Components.objects.get(id=component_id)
    except Components.DoesNotExist:
        return JsonResponse({"error": "Component not found"}, status=404)

    old_value = getattr(component, field, None)

    if str(old_value) == str(cast_value):
        return JsonResponse({"status": "no_change"})

    # Save and audit atomically
    try:
        with transaction.atomic():
            setattr(component, field, cast_value)
            component.save(update_fields=[field])

            ComponentAudit.objects.create(
                component_id=component.id,
                field=field,
                old_value=None if old_value is None else str(old_value),
                new_value=None if cast_value is None else str(cast_value),
                user=request.user,
                source="inline",
            )
    except Exception as e:
        return JsonResponse({"error": f"Failed to update: {e}"}, status=500)

    return JsonResponse({"status": "ok", "field": field, "value": cast_value})


