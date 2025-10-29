from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('browse/', views.browse_flagship, name='browse_flagship'),
    
    # Live catalog views (unified implementation)
    path('products/', views.index, name='index'),
    path('components/', views.components_index, name='components_index'),
    
    # Product detail view
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),
    path('components/<uuid:component_id>/', views.component_detail, name='component_detail'),
    path('learn/', views.learning_index, name='learning_index'),
    path('learn/<slug:slug>/', views.learning_detail, name='learning_detail'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # API endpoints
    path('api/search-suggestions/', views.api_search_suggestions, name='api_search_suggestions'),
    path('api/filter-options/', views.api_filter_options, name='api_filter_options'),
    path('api/quick-info/<uuid:item_id>/', views.api_quick_info, name='api_quick_info'),
    path('api/compare-components/', views.api_compare_components, name='api_compare_components'),
]