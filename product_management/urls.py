from django.urls import path

from product_management.views import (
    bare_tool_create_view,
    batch_component_edit_view,
    batch_product_edit_view,
    bundle_create_view,
    component_quick_create_view,
    dashboard_view,
    extract_component_from_product_view,
    undo_last_change_view,
    product_quick_create_view,
)
from product_management.views import api as api_views
from product_management.views.manufacturer_import import (
    import_preview_approve_view,
    import_preview_cancel_view,
    manufacturer_import_view,
)

app_name = "product_management"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("bare-tool/create/", bare_tool_create_view, name="bare_tool_create"),
    path("components/quick-create/", component_quick_create_view, name="component_quick_create"),
    path("products/quick-create/", product_quick_create_view, name="product_quick_create"),
    path("bundles/create/", bundle_create_view, name="bundle_create"),
    path(
        "products/<uuid:product_id>/extract-component/",
        extract_component_from_product_view,
        name="extract_component_from_product",
    ),
    path(
        "audit/<str:entity_type>/<uuid:entity_id>/undo/",
        undo_last_change_view,
        name="undo_last_change",
    ),
    path("api/components/search/", api_views.component_search, name="api_component_search"),
    path("api/products/search/", api_views.product_search, name="api_product_search"),
    path("batch/components/edit/", batch_component_edit_view, name="batch_component_edit"),
    path("batch/products/edit/", batch_product_edit_view, name="batch_product_edit"),
    path("import/", manufacturer_import_view, name="manufacturer_import"),
    path("import/approve/", import_preview_approve_view, name="import_preview_approve"),
    path("import/cancel/", import_preview_cancel_view, name="import_preview_cancel"),
]



