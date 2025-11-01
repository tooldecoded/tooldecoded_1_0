from __future__ import annotations

from typing import Dict, Iterable, Optional

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from product_management.forms import (
    BareToolForm,
    BundleProductForm,
    ComponentQuickForm,
    ComponentSelectorForm,
    ProductQuickForm,
    ProductSelectorForm,
)
from product_management.services import extract_component_from_product
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
    return forms


def _component_results(selector_form: ComponentSelectorForm, limit: int = 25) -> Iterable[Components]:
    if not selector_form.is_bound or not selector_form.is_valid():
        return []
    q = selector_form.cleaned_data.get("q") or ""
    brand = selector_form.cleaned_data.get("brand")
    queryset = Components.objects.select_related("brand").order_by(
        "brand__name", "sku", "name"
    )
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand:
        queryset = queryset.filter(brand=brand)
    return queryset[:limit]


def _product_results(selector_form: ProductSelectorForm, limit: int = 25) -> Iterable[Products]:
    if not selector_form.is_bound or not selector_form.is_valid():
        return []
    q = selector_form.cleaned_data.get("q") or ""
    brand = selector_form.cleaned_data.get("brand")
    queryset = Products.objects.select_related("brand").order_by(
        "brand__name", "sku", "name"
    )
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if brand:
        queryset = queryset.filter(brand=brand)
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

    context: Dict[str, object] = {
        "page_title": "Product & Component Backoffice",
        "bare_tool_form": forms["bare_tool_form"],
        "bundle_form": forms["bundle_form"],
        "component_form": forms["component_form"],
        "product_form": forms["product_form"],
        "component_selector": component_selector,
        "product_selector": product_selector,
        "component_results": _component_results(component_selector),
        "product_results": _product_results(product_selector),
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
