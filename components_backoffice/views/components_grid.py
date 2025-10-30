from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from toolanalysis.models import Components


def _ensure_feature_enabled():
    if not getattr(settings, "ENABLE_COMPONENTS_BACKOFFICE", False):
        raise Http404()


def components_grid_view(request):
    _ensure_feature_enabled()
    # Superuser-only access
    if not getattr(request.user, "is_authenticated", False) or not getattr(request.user, "is_superuser", False):
        raise Http404()

    page_size_default = getattr(settings, "COMP_BACKOFFICE_PAGE_SIZE", 50)
    page_size_max = getattr(settings, "COMP_BACKOFFICE_MAX_PAGE_SIZE", 200)

    q = request.GET.get("q")
    queryset = Components.objects.all().order_by("id")
    if q:
        queryset = queryset.filter(name__icontains=q)

    try:
        page_size = min(int(request.GET.get("page_size", page_size_default)), page_size_max)
    except Exception:
        page_size = page_size_default

    paginator = Paginator(queryset, page_size)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Build page size options (respect max)
    available_sizes = [50, 100, 150, 200]
    page_size_options = [s for s in available_sizes if s <= page_size_max]

    # Dynamically derive displayable fields from the model
    # Exclude very large or low-value fields
    excluded_field_names = {"description", "fair_price_narrative", "image"}
    model_fields = []
    for f in Components._meta.fields:
        if f.name in excluded_field_names:
            continue
        # Include simple fields and FKs (M2M are not in _meta.fields)
        model_fields.append({
            "name": f.name,
            "label": getattr(f, "verbose_name", f.name).title(),
        })

    # Prefer a sensible default order when available
    preferred_order = [
        "id",
        "sku",
        "name",
        "brand",
        "listingtype",
        "is_featured",
        "standalone_price",
        "showcase_priority",
    ]
    # Sort fields by preferred order first, then by name
    order_index = {n: i for i, n in enumerate(preferred_order)}
    model_fields.sort(key=lambda f: (order_index.get(f["name"], 1_000_000), f["name"]))

    context = {
        "page_obj": page_obj,
        "q": q or "",
        "page_size": page_size,
        "page_size_options": page_size_options,
        "columns": model_fields,
    }
    return render(request, "components_backoffice/components_grid.html", context)


