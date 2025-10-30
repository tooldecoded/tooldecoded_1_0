from django.urls import path

from .views.detail import (
    component_create_view,
    component_detail_view,
    component_delete_view,
    components_editor_list_view,
    component_inline_update_view_idfree,
)

app_name = "components_backoffice"

urlpatterns = [
    path("components/", components_editor_list_view, name="components_list"),
    path("components/new/", component_create_view, name="component_create"),
    path(
        "components/<slug:brand_slug>/<slug:sku_or_nk>/",
        component_detail_view,
        name="component_detail",
    ),
    path(
        "components/<slug:brand_slug>/<slug:sku_or_nk>/inline/",
        component_inline_update_view_idfree,
        name="component_inline_update",
    ),
    path(
        "components/<slug:brand_slug>/<slug:sku_or_nk>/delete/",
        component_delete_view,
        name="component_delete",
    ),
]


