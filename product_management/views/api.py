from __future__ import annotations

from typing import List

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from toolanalysis.models import Components, Products

from . import _ensure_feature_enabled, _ensure_superuser


DEFAULT_LIMIT = 25
MAX_LIMIT = getattr(settings, "COMP_BACKOFFICE_MAX_PAGE_SIZE", 200)


def _parse_limit(raw: str | None) -> int:
    try:
        value = int(raw) if raw is not None else DEFAULT_LIMIT
    except (TypeError, ValueError):
        value = DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


def _serialize_components(components: List[Components]) -> List[dict]:
    return [
        {
            "id": str(component.id),
            "name": component.name,
            "sku": component.sku,
            "brand": getattr(component.brand, "name", None),
        }
        for component in components
    ]


def _serialize_products(products: List[Products]) -> List[dict]:
    return [
        {
            "id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "brand": getattr(product.brand, "name", None),
        }
        for product in products
    ]


@require_GET
def component_search(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    q = (request.GET.get("q") or "").strip()
    brand_id = request.GET.get("brand")
    limit = _parse_limit(request.GET.get("limit"))

    queryset = Components.objects.select_related("brand").order_by("brand__name", "sku", "name")
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)

    sample = list(queryset[: limit + 1])
    has_more = len(sample) > limit
    results = _serialize_components(sample[:limit])

    return JsonResponse({
        "results": results,
        "has_more": has_more,
        "limit": limit,
    })


@require_GET
def product_search(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    q = (request.GET.get("q") or "").strip()
    brand_id = request.GET.get("brand")
    limit = _parse_limit(request.GET.get("limit"))

    queryset = Products.objects.select_related("brand").order_by("brand__name", "sku", "name")
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)

    sample = list(queryset[: limit + 1])
    has_more = len(sample) > limit
    results = _serialize_products(sample[:limit])

    return JsonResponse({
        "results": results,
        "has_more": has_more,
        "limit": limit,
    })

