from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.index, name='index'),
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('components/', views.components_index, name='components_index'),
    path('components/<uuid:component_id>/', views.component_detail, name='component_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
