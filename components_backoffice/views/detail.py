from typing import Optional

from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from components_backoffice.forms import ComponentForm
from components_backoffice.models import ComponentAudit
from toolanalysis.models import Brands, Components, Attributes, ComponentAttributes, Features, ComponentFeatures, ProductLines


def _ensure_feature_enabled():
    if not getattr(settings, "ENABLE_COMPONENTS_BACKOFFICE", False):
        raise Http404()


def _get_component_by_human_key(brand_slug: str, sku_or_nk: str) -> Components:
    # Resolve brand by slug to name, case-insensitive
    brand = get_object_or_404(Brands, name__iexact=brand_slug.replace("-", " "))
    # Primary: (brand, sku)
    try:
        return Components.objects.select_related("brand").get(
            brand=brand, sku=sku_or_nk
        )
    except Components.DoesNotExist:
        # Optional future: lookup via a mapping table for natural_key
        raise Http404()


def components_editor_list_view(request):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()

    page_size_default = getattr(settings, "COMP_BACKOFFICE_PAGE_SIZE", 50)
    q = request.GET.get("q")
    queryset = Components.objects.select_related("brand").all().order_by("name")
    if q:
        queryset = queryset.filter(name__icontains=q)

    paginator = Paginator(queryset, page_size_default)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "components_backoffice/components_editor/components_grid.html",
        {
            "page_obj": page_obj,
            "q": q or "",
        },
    )


def component_create_view(request):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()

    if request.method == "POST":
        form = ComponentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                component = form.save()
                try:
                    form.save_m2m()
                except Exception:
                    pass
                # minimal audit entry for creation
                ComponentAudit.objects.create(
                    component_id=component.id,
                    field="__create__",
                    old_value=None,
                    new_value=f"brand={getattr(component.brand,'name',None)}, sku={component.sku}",
                    user=request.user,
                    source="form",
                )
            return redirect(
                "components_backoffice_editor:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else "unknown",
                sku_or_nk=component.sku or "unknown",
            )
    else:
        form = ComponentForm()

    return render(
        request,
        "components_backoffice/components_editor/detail.html",
        {"form": form, "is_create": True},
    )


def component_detail_view(request, brand_slug: str, sku_or_nk: str):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()

    component = _get_component_by_human_key(brand_slug, sku_or_nk)

    # Build selector data (brand filter + search)
    select_brand = request.GET.get("select_brand")
    select_q = request.GET.get("select_q", "").strip()
    brands = list(Brands.objects.all().order_by("name"))
    selector_qs = Components.objects.select_related("brand").all()
    if select_brand:
        selector_qs = selector_qs.filter(brand__name__iexact=select_brand)
    if select_q:
        selector_qs = selector_qs.filter(name__icontains=select_q)
    selector_qs = list(selector_qs.order_by("brand__name", "sku", "name"))

    if request.method == "POST":
        # Reset button discards any changes and reloads from DB
        if request.POST.get("reset"):
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )

        # Attribute management actions
        action = request.POST.get("action")
        if action == "attr_add":
            try:
                attr_id = request.POST.get("attribute_id")
                value = (request.POST.get("value") or "").strip() or None
                attribute = Attributes.objects.get(id=attr_id)
                with transaction.atomic():
                    ComponentAttributes.objects.create(
                        component=component,
                        attribute=attribute,
                        value=value,
                    )
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        elif action == "attr_update":
            try:
                comp_attr_id = request.POST.get("comp_attr_id")
                value = (request.POST.get("value") or "").strip() or None
                with transaction.atomic():
                    ca = ComponentAttributes.objects.get(id=comp_attr_id, component=component)
                    ca.value = value
                    ca.save(update_fields=["value"])
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        elif action == "attr_delete":
            try:
                comp_attr_id = request.POST.get("comp_attr_id")
                with transaction.atomic():
                    ComponentAttributes.objects.filter(id=comp_attr_id, component=component).delete()
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        # Feature value actions (manual list UI)
        elif action == "feat_add":
            try:
                feat_id = request.POST.get("feature_id")
                value = (request.POST.get("value") or "").strip() or None
                feature = Features.objects.get(id=feat_id)
                with transaction.atomic():
                    # Ensure only one row per (component, feature)
                    ComponentFeatures.objects.filter(component=component, feature=feature).delete()
                    ComponentFeatures.objects.create(component=component, feature=feature, value=value)
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        elif action == "feat_update":
            try:
                comp_feat_id = request.POST.get("comp_feat_id")
                value = (request.POST.get("value") or "").strip() or None
                with transaction.atomic():
                    cf = ComponentFeatures.objects.get(id=comp_feat_id, component=component)
                    cf.value = value
                    cf.save(update_fields=["value"])
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        elif action == "feat_delete":
            try:
                comp_feat_id = request.POST.get("comp_feat_id")
                with transaction.atomic():
                    ComponentFeatures.objects.filter(id=comp_feat_id, component=component).delete()
            except Exception:
                pass
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(component.brand.name) if component.brand else brand_slug,
                sku_or_nk=component.sku or sku_or_nk,
            )
        form = ComponentForm(request.POST, instance=component)
        # Narrow dependent querysets (e.g., product lines by brand) based on submitted brand or instance brand
        try:
            submitted_brand_id = request.POST.get("brand")
            brand_for_filter = None
            if submitted_brand_id:
                brand_for_filter = Brands.objects.filter(id=submitted_brand_id).first()
            if not brand_for_filter:
                brand_for_filter = getattr(component, "brand", None)
            if brand_for_filter and "productlines" in form.fields:
                form.fields["productlines"].queryset = ProductLines.objects.filter(brand=brand_for_filter).order_by("name")
        except Exception:
            pass
        if form.is_valid():
            with transaction.atomic():
                before = {f: getattr(component, f) for f in form.changed_data}
                updated = form.save()
                # Persist M2M relations (features, itemtypes, etc.)
                try:
                    form.save_m2m()
                except Exception:
                    pass
                # No ComponentFeatures value reconciliation; rely solely on M2M selection
                for field_name in form.changed_data:
                    old_value = None if before[field_name] is None else str(before[field_name])
                    new_value = None if getattr(updated, field_name) is None else str(
                        getattr(updated, field_name)
                    )
                    ComponentAudit.objects.create(
                        component_id=updated.id,
                        field=field_name,
                        old_value=old_value,
                        new_value=new_value,
                        user=request.user,
                        source="form",
                    )
            return redirect(
                "components_backoffice:component_detail",
                brand_slug=slugify(updated.brand.name) if updated.brand else brand_slug,
                sku_or_nk=updated.sku or sku_or_nk,
            )
    else:
        form = ComponentForm(instance=component)
        # Narrow dependent querysets on initial load using the component's brand
        try:
            brand_for_filter = getattr(component, "brand", None)
            if brand_for_filter and "productlines" in form.fields:
                form.fields["productlines"].queryset = ProductLines.objects.filter(brand=brand_for_filter).order_by("name")
        except Exception:
            pass
        # Ensure features chosen list preselects any applied features or existing ComponentFeatures
        try:
            if "features" in form.fields:
                selected_feature_ids = set(
                    ComponentFeatures.objects.filter(component=component).values_list("feature_id", flat=True)
                )
                try:
                    selected_feature_ids.update(component.features.values_list("id", flat=True))
                except Exception:
                    pass
                form.fields["features"].initial = list(selected_feature_ids)
        except Exception:
            pass

    audits = list(ComponentAudit.objects.filter(component_id=component.id).order_by("-created_at")[:50])
    comp_attributes = list(
        ComponentAttributes.objects.select_related("attribute")
        .filter(component=component)
        .order_by("attribute__name", "value")
    )
    all_attributes = list(Attributes.objects.all().order_by("name"))

    # Current feature rows for manual editing list
    comp_features = list(
        ComponentFeatures.objects.select_related("feature")
        .filter(component=component)
        .order_by("feature__name", "value")
    )
    all_features = list(Features.objects.all().order_by("name"))

    # Highlight attributes associated with this component's itemtypes
    try:
        itemtype_ids = list(component.itemtypes.values_list("id", flat=True))
        highlight_attr_ids = list(
            Attributes.objects.filter(itemtypes__id__in=itemtype_ids)
            .values_list("id", flat=True)
            .distinct()
        )
    except Exception:
        highlight_attr_ids = []

    return render(
        request,
        "components_backoffice/components_editor/detail.html",
        {
            "form": form,
            "component": component,
            "audits": audits,
            "is_create": False,
            "brands": brands,
            "select_brand": select_brand or "",
            "select_q": select_q,
            "selector_components": selector_qs,
            "comp_attributes": comp_attributes,
            "all_attributes": all_attributes,
            "comp_features": comp_features,
            "all_features": all_features,
            "highlight_attribute_ids": [str(x) for x in highlight_attr_ids],
        },
    )


def component_delete_view(request, brand_slug: str, sku_or_nk: str):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()

    component = _get_component_by_human_key(brand_slug, sku_or_nk)

    if request.method == "POST":
        with transaction.atomic():
            ComponentAudit.objects.create(
                component_id=component.id,
                field="__delete__",
                old_value=str(component.name),
                new_value=None,
                user=request.user,
                source="form",
            )
            component.delete()
        return redirect("components_backoffice:components_list")

    return render(
        request,
        "components_backoffice/components_editor/delete_confirm.html",
        {"component": component},
    )


def component_inline_update_view_idfree(request, brand_slug: str, sku_or_nk: str):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    component = _get_component_by_human_key(brand_slug, sku_or_nk)

    try:
        payload = request.POST or {}
        if request.content_type and "application/json" in request.content_type.lower():
            import json

            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    field = payload.get("field")
    value = payload.get("value")
    if field not in {"name", "is_featured", "standalone_price", "showcase_priority"}:
        return JsonResponse({"error": "Field not editable inline"}, status=400)

    try:
        if field == "is_featured":
            v = str(value).strip().lower()
            cast_value = v in {"true", "1", "yes", "y", "on"}
        elif field in {"standalone_price"}:
            cast_value = None if value in ("", None) else float(value)
        elif field in {"showcase_priority"}:
            cast_value = int(value)
        else:
            cast_value = value
    except Exception as e:
        return JsonResponse({"error": f"Invalid value: {e}"}, status=400)

    old_value = getattr(component, field, None)
    if str(old_value) == str(cast_value):
        return JsonResponse({"status": "no_change"})

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

    return JsonResponse({"status": "ok", "field": field, "value": cast_value})


