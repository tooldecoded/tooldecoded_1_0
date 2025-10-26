from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('components/', views.components_index, name='components_index'),
    path('components/<uuid:component_id>/', views.component_detail, name='component_detail'),
]
