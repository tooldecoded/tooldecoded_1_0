from __future__ import annotations

from typing import Dict, Iterable

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from product_management.forms import (
    BareToolForm,
    BatchComponentEditForm,
    BatchProductEditForm,
    BundleProductForm,
    BundleProductSelectorForm,
    ComponentQuickForm,
    ComponentSelectorForm,
    ProductQuickForm,
    ProductSelectorForm,
)
from product_management.forms.manufacturer_import import ManufacturerImportForm
from product_management.services import (
    batch_update_components,
    batch_update_products,
    extract_component_from_product,
    undo_last_change,
)
from toolanalysis.models import Components, Products


def _ensure_feature_enabled() -> None:
    if not getattr(settings, "ENABLE_PRODUCT_MANAGEMENT_BACKOFFICE", False):
        raise Http404()


def _ensure_superuser(request) -> None:
    if not getattr(request.user, "is_authenticated", False) or not getattr(
        request.user, "is_superuser", False
    ):
        raise Http404()


def _dashboard_forms(request, **overrides) -> Dict[str, object]:
    forms: Dict[str, object] = {}
    forms["bare_tool_form"] = overrides.get("bare_tool_form") or BareToolForm(
        prefix="bare_tool"
    )
    forms["bundle_form"] = overrides.get("bundle_form") or BundleProductForm(
        prefix="bundle"
    )
    forms["component_form"] = overrides.get("component_form") or ComponentQuickForm(
        prefix="component"
    )
    forms["product_form"] = overrides.get("product_form") or ProductQuickForm(
        prefix="product"
    )
    forms["component_selector"] = overrides.get("component_selector") or ComponentSelectorForm(
        request.GET or None, prefix="component_filter"
    )
    forms["product_selector"] = overrides.get("product_selector") or ProductSelectorForm(
        request.GET or None, prefix="product_filter"
    )
    forms["batch_component_form"] = overrides.get("batch_component_form") or BatchComponentEditForm(
        prefix="batch_component"
    )
    forms["batch_product_form"] = overrides.get("batch_product_form") or BatchProductEditForm(
        prefix="batch_product"
    )
    forms["bundle_selector"] = overrides.get("bundle_selector") or BundleProductSelectorForm(
        request.GET or None, prefix="bundle_filter"
    )
    forms["import_form"] = overrides.get("import_form") or ManufacturerImportForm(prefix="url")
    from product_management.forms.manufacturer_import import ManufacturerHTMLImportForm
    forms["import_html_form"] = overrides.get("import_html_form") or ManufacturerHTMLImportForm(prefix="html")
    return forms


def _component_results(selector_form: ComponentSelectorForm, limit: int = 25) -> Iterable[Components]:
    if not selector_form.is_bound or not selector_form.is_valid():
        return []
    q = selector_form.cleaned_data.get("q") or ""
    brand = selector_form.cleaned_data.get("brand")
    motortype = selector_form.cleaned_data.get("motortype")
    listingtype = selector_form.cleaned_data.get("listingtype")
    itemtypes = selector_form.cleaned_data.get("itemtype")
    categories = selector_form.cleaned_data.get("category")
    componentclass = selector_form.cleaned_data.get("componentclass")
    is_featured = selector_form.cleaned_data.get("is_featured")
    isaccessory = selector_form.cleaned_data.get("isaccessory")
    
    queryset = Components.objects.select_related("brand", "motortype", "listingtype", "componentclass").order_by(
        "brand__name", "sku", "name"
    )
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand:
        queryset = queryset.filter(brand=brand)
    if motortype:
        queryset = queryset.filter(motortype=motortype)
    if listingtype:
        queryset = queryset.filter(listingtype=listingtype)
    if componentclass:
        queryset = queryset.filter(componentclass=componentclass)
    if is_featured:
        queryset = queryset.filter(is_featured=True)
    if isaccessory:
        queryset = queryset.filter(isaccessory=True)
    if itemtypes:
        queryset = queryset.filter(itemtypes__in=itemtypes).distinct()
    if categories:
        queryset = queryset.filter(categories__in=categories).distinct()
    return queryset[:limit]


def _bundle_product_results(selector_form: BundleProductSelectorForm, limit: int = 50) -> Iterable[Products]:
    """Get products that have components for bundling."""
    if not selector_form.is_bound or not selector_form.is_valid():
        return []
    q = selector_form.cleaned_data.get("q") or ""
    brand = selector_form.cleaned_data.get("brand")
    motortype = selector_form.cleaned_data.get("motortype")
    listingtype = selector_form.cleaned_data.get("listingtype")
    status = selector_form.cleaned_data.get("status")
    itemtypes = selector_form.cleaned_data.get("itemtype")
    categories = selector_form.cleaned_data.get("category")
    
    from toolanalysis.models import ProductComponents
    # Only products that have components
    queryset = Products.objects.filter(
        id__in=ProductComponents.objects.values_list("product_id", flat=True).distinct()
    ).select_related("brand", "motortype", "listingtype", "status").prefetch_related(
        "productcomponents_set"
    ).order_by(
        "brand__name", "sku", "name"
    )
    
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand:
        queryset = queryset.filter(brand=brand)
    if motortype:
        queryset = queryset.filter(motortype=motortype)
    if listingtype:
        queryset = queryset.filter(listingtype=listingtype)
    if status:
        queryset = queryset.filter(status=status)
    if itemtypes:
        queryset = queryset.filter(itemtypes__in=itemtypes).distinct()
    if categories:
        queryset = queryset.filter(categories__in=categories).distinct()
    return queryset[:limit]


def _product_results(selector_form: ProductSelectorForm, limit: int = 25) -> Iterable[Products]:
    if not selector_form.is_bound or not selector_form.is_valid():
        return []
    q = selector_form.cleaned_data.get("q") or ""
    brand = selector_form.cleaned_data.get("brand")
    motortype = selector_form.cleaned_data.get("motortype")
    listingtype = selector_form.cleaned_data.get("listingtype")
    status = selector_form.cleaned_data.get("status")
    itemtypes = selector_form.cleaned_data.get("itemtype")
    categories = selector_form.cleaned_data.get("category")
    isaccessory = selector_form.cleaned_data.get("isaccessory")
    
    queryset = Products.objects.select_related("brand", "motortype", "listingtype", "status").order_by(
        "brand__name", "sku", "name"
    )
    
    # Exclude products that already have components (bundles)
    # These are products that shouldn't be extracted as components
    from toolanalysis.models import ProductComponents
    queryset = queryset.exclude(id__in=ProductComponents.objects.values_list("product_id", flat=True).distinct())
    
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand:
        queryset = queryset.filter(brand=brand)
    if motortype:
        queryset = queryset.filter(motortype=motortype)
    if listingtype:
        queryset = queryset.filter(listingtype=listingtype)
    if status:
        queryset = queryset.filter(status=status)
    if isaccessory:
        queryset = queryset.filter(isaccessory=True)
    if itemtypes:
        queryset = queryset.filter(itemtypes__in=itemtypes).distinct()
    if categories:
        queryset = queryset.filter(categories__in=categories).distinct()
    return queryset[:limit]


def _dashboard_context(request, **overrides) -> Dict[str, object]:
    forms = _dashboard_forms(
        request,
        bare_tool_form=overrides.get("bare_tool_form"),
        bundle_form=overrides.get("bundle_form"),
        component_form=overrides.get("component_form"),
        product_form=overrides.get("product_form"),
        component_selector=overrides.get("component_selector"),
        product_selector=overrides.get("product_selector"),
    )

    component_selector = forms["component_selector"]
    product_selector = forms["product_selector"]
    bundle_selector = forms["bundle_selector"]

    context: Dict[str, object] = {
        "page_title": "Product & Component Backoffice",
        "bare_tool_form": forms["bare_tool_form"],
        "bundle_form": forms["bundle_form"],
        "bundle_selector": bundle_selector,
        "component_form": forms["component_form"],
        "product_form": forms["product_form"],
        "component_selector": component_selector,
        "product_selector": product_selector,
        "component_results": _component_results(component_selector),
        "product_results": _product_results(product_selector),
        "bundle_product_results": _bundle_product_results(bundle_selector),
        "batch_component_form": forms["batch_component_form"],
        "batch_product_form": forms["batch_product_form"],
        "batch_component_ids": overrides.get("batch_component_ids", ""),
        "batch_product_ids": overrides.get("batch_product_ids", ""),
        "import_form": forms["import_form"],
        "import_html_form": forms["import_html_form"],
        "active_tab": overrides.get("active_tab", request.GET.get("tab", "quick")),
    }
    return context


def _redirect_with_tab(tab: str):
    url = reverse("product_management:dashboard")
    return redirect(f"{url}?tab={tab}")


@require_http_methods(["GET"])
def dashboard_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)
    context = _dashboard_context(request)
    return render(request, "product_management/dashboard.html", context)


@require_http_methods(["POST"])
def bare_tool_create_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    form = BareToolForm(request.POST, prefix="bare_tool")
    if form.is_valid():
        component, product = form.save(user=request.user)
        if product:
            messages.success(
                request,
                f"Created component '{component.name}' and linked product '{product.name}'.",
            )
        else:
            messages.success(request, f"Created component '{component.name}'.")
        return _redirect_with_tab("quick")

    context = _dashboard_context(request, bare_tool_form=form, active_tab="quick")
    return render(request, "product_management/dashboard.html", context, status=400)


@require_http_methods(["POST"])
def component_quick_create_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    form = ComponentQuickForm(request.POST, prefix="component")
    if form.is_valid():
        component = form.save()
        messages.success(request, f"Created component '{component.name}'.")
        return _redirect_with_tab("quick")

    context = _dashboard_context(request, component_form=form, active_tab="quick")
    return render(request, "product_management/dashboard.html", context, status=400)


@require_http_methods(["POST"])
def product_quick_create_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    form = ProductQuickForm(request.POST, prefix="product")
    if form.is_valid():
        product = form.save()
        messages.success(request, f"Created product '{product.name}'.")
        return _redirect_with_tab("quick")

    context = _dashboard_context(request, product_form=form, active_tab="quick")
    return render(request, "product_management/dashboard.html", context, status=400)


@require_http_methods(["POST"])
def bundle_create_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    form = BundleProductForm(request.POST, prefix="bundle")
    if form.is_valid():
        product = form.save(user=request.user)
        messages.success(request, f"Created bundled product '{product.name}'.")
        return _redirect_with_tab("bundles")

    context = _dashboard_context(request, bundle_form=form, active_tab="bundles")
    return render(request, "product_management/dashboard.html", context, status=400)


@require_POST
def extract_component_from_product_view(request, product_id: str):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    product = get_object_or_404(Products, id=product_id)
    overrides = {}
    name = request.POST.get("component_name")
    sku = request.POST.get("component_sku")
    if name:
        overrides["name"] = name
    if sku:
        overrides["sku"] = sku

    component = extract_component_from_product(product, overrides=overrides, user=request.user)
    messages.success(
        request,
        f"Created component '{component.name}' from product '{product.name}'.",
    )
    return _redirect_with_tab("relationships")


@require_POST
def undo_last_change_view(request, entity_type: str, entity_id: str):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    try:
        undo_last_change(entity_type, entity_id, user=request.user)
    except ValidationError as exc:
        messages.error(request, ", ".join(exc.messages))
    else:
        messages.success(request, "Reverted the most recent change.")

    tab = request.POST.get("tab") or "relationships"
    return _redirect_with_tab(tab)


@require_http_methods(["GET", "POST"])
def batch_component_edit_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    component_ids_str = request.GET.get("ids") or request.POST.get("component_ids", "")
    
    if request.method == "POST":
        form = BatchComponentEditForm(request.POST)
        if form.is_valid():
            component_ids = form.cleaned_data["component_ids"]
            updates = {}
            
            # Only include fields that were actually provided (non-empty/None)
            if form.cleaned_data.get("brand"):
                updates["brand"] = form.cleaned_data["brand"]
            if form.cleaned_data.get("listingtype"):
                updates["listingtype"] = form.cleaned_data["listingtype"]
            if form.cleaned_data.get("motortype"):
                updates["motortype"] = form.cleaned_data["motortype"]
            if form.cleaned_data.get("componentclass"):
                updates["componentclass"] = form.cleaned_data["componentclass"]
            # For boolean fields, only update if explicitly checked (True)
            if form.cleaned_data.get("is_featured"):
                updates["is_featured"] = True
            if form.cleaned_data.get("isaccessory"):
                updates["isaccessory"] = True
            # Text fields - only update if non-empty
            image_val = form.cleaned_data.get("image", "").strip()
            if image_val:
                updates["image"] = image_val
            description_val = form.cleaned_data.get("description", "").strip()
            if description_val:
                updates["description"] = description_val
            if form.cleaned_data.get("showcase_priority") is not None:
                updates["showcase_priority"] = form.cleaned_data["showcase_priority"]
            if form.cleaned_data.get("standalone_price") is not None:
                updates["standalone_price"] = form.cleaned_data["standalone_price"]
            # M2M fields - only update if provided
            if form.cleaned_data.get("itemtypes"):
                updates["itemtypes"] = form.cleaned_data["itemtypes"]
            if form.cleaned_data.get("categories"):
                updates["categories"] = form.cleaned_data["categories"]
            if form.cleaned_data.get("subcategories"):
                updates["subcategories"] = form.cleaned_data["subcategories"]
            if form.cleaned_data.get("batteryplatforms"):
                updates["batteryplatforms"] = form.cleaned_data["batteryplatforms"]
            if form.cleaned_data.get("batteryvoltages"):
                updates["batteryvoltages"] = form.cleaned_data["batteryvoltages"]
            if form.cleaned_data.get("productlines"):
                updates["productlines"] = form.cleaned_data["productlines"]
            if form.cleaned_data.get("features"):
                updates["features"] = form.cleaned_data["features"]
            
            if updates:
                count = batch_update_components(component_ids, updates, user=request.user)
                messages.success(request, f"Updated {count} component(s).")
                return _redirect_with_tab("batch")
            else:
                messages.info(request, "No changes to apply.")
    else:
        form = BatchComponentEditForm(initial={"component_ids": component_ids_str})

    context = _dashboard_context(
        request,
        batch_component_form=form,
        batch_component_ids=component_ids_str,
        active_tab="batch",
    )
    return render(request, "product_management/dashboard.html", context)


@require_http_methods(["GET", "POST"])
def batch_product_edit_view(request):
    _ensure_feature_enabled()
    _ensure_superuser(request)

    product_ids_str = request.GET.get("ids") or request.POST.get("product_ids", "")
    
    if request.method == "POST":
        form = BatchProductEditForm(request.POST)
        if form.is_valid():
            product_ids = form.cleaned_data["product_ids"]
            updates = {}
            
            # Only include fields that were actually provided (non-empty/None)
            if form.cleaned_data.get("brand"):
                updates["brand"] = form.cleaned_data["brand"]
            if form.cleaned_data.get("listingtype"):
                updates["listingtype"] = form.cleaned_data["listingtype"]
            if form.cleaned_data.get("motortype"):
                updates["motortype"] = form.cleaned_data["motortype"]
            if form.cleaned_data.get("status"):
                updates["status"] = form.cleaned_data["status"]
            # For boolean fields, only update if explicitly checked (True)
            if form.cleaned_data.get("isaccessory"):
                updates["isaccessory"] = True
            # Text fields - only update if non-empty
            image_val = form.cleaned_data.get("image", "").strip()
            if image_val:
                updates["image"] = image_val
            description_val = form.cleaned_data.get("description", "").strip()
            if description_val:
                updates["description"] = description_val
            bullets_val = form.cleaned_data.get("bullets", "").strip()
            if bullets_val:
                updates["bullets"] = bullets_val
            # M2M fields - only update if provided
            if form.cleaned_data.get("itemtypes"):
                updates["itemtypes"] = form.cleaned_data["itemtypes"]
            if form.cleaned_data.get("categories"):
                updates["categories"] = form.cleaned_data["categories"]
            if form.cleaned_data.get("subcategories"):
                updates["subcategories"] = form.cleaned_data["subcategories"]
            if form.cleaned_data.get("batteryplatforms"):
                updates["batteryplatforms"] = form.cleaned_data["batteryplatforms"]
            if form.cleaned_data.get("batteryvoltages"):
                updates["batteryvoltages"] = form.cleaned_data["batteryvoltages"]
            if form.cleaned_data.get("features"):
                updates["features"] = form.cleaned_data["features"]
            
            if updates:
                count = batch_update_products(product_ids, updates, user=request.user)
                messages.success(request, f"Updated {count} product(s).")
                return _redirect_with_tab("batch")
            else:
                messages.info(request, "No changes to apply.")
    else:
        form = BatchProductEditForm(initial={"product_ids": product_ids_str})

    context = _dashboard_context(
        request,
        batch_product_form=form,
        batch_product_ids=product_ids_str,
        active_tab="batch",
    )
    return render(request, "product_management/dashboard.html", context)
