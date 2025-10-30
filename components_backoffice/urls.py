from django.urls import path

from .views.dashboard import dashboard_view
from .views.components_grid import components_grid_view
from .views.inline import component_inline_update_view

app_name = "components_backoffice"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("components/", components_grid_view, name="components_grid"),
    path("components/<uuid:component_id>/inline/", component_inline_update_view, name="component_inline_update"),
]


