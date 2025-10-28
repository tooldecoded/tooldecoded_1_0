from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, Value, F, FloatField
from django.db.models.functions import Cast
from django.http import JsonResponse
import uuid
from toolanalysis.models import (
    Products, Components, Brands, BatteryVoltages, BatteryPlatforms, 
    ItemCategories, Statuses, ListingTypes, ComponentAttributes, Attributes,
    ProductLines, ProductComponents
)
from .models import LearningArticle, Tag, SiteSettings
from .utils import get_category_hierarchy_filters, build_category_hierarchy_data

# ============================================================================
# FLAGSHIP PRODUCTS CONFIGURATION
# ============================================================================
# Add SKUs of products to showcase in the Browse Flagship section
# These should represent each brand's current flagship offering per category
# 
# To add products:
# 1. Find the product SKU from your database
# 2. Add it to the list below with a comment for reference
# 3. Products will be automatically organized by category and brand
#
# Example:
#   '2804-20',  # Milwaukee M18 FUEL Hammer Drill
#
FLAGSHIP_PRODUCT_SKUS = [
    2904-20,
     # User will populate this list
]

def index(request):
    """Product catalog with comprehensive filtering and pagination"""
    # Get filter parameters
    search = request.GET.get('search', '')
    brand = request.GET.get('brand', '')
    voltage = request.GET.get('voltage', '')
    platform = request.GET.get('platform', '')
    category_level1 = request.GET.get('category_level1', '')
    category_level2 = request.GET.get('category_level2', '')
    category_level3 = request.GET.get('category_level3', '')
    status = request.GET.get('status', '')
    release_date_from = request.GET.get('release_date_from', '')
    release_date_to = request.GET.get('release_date_to', '')
    sort = request.GET.get('sort', 'name')
    sort_direction = request.GET.get('sort_direction', 'asc')
    page = int(request.GET.get('page', 1))
    
    
    # Parse multi-select values
    brand_ids = request.GET.getlist('brand')
    voltage_ids = request.GET.getlist('voltage')
    platform_ids = request.GET.getlist('platform')
    status_ids = request.GET.getlist('status')
    
    # Handle comma-separated values if no individual values
    if not brand_ids and brand:
        brand_ids = [x.strip() for x in brand.split(',')]
    if not voltage_ids and voltage:
        voltage_ids = [x.strip() for x in voltage.split(',')]
    if not platform_ids and platform:
        platform_ids = [x.strip() for x in platform.split(',')]
    if not status_ids and status:
        status_ids = [x.strip() for x in status.split(',')]
    
    # Convert string IDs to UUIDs for database filtering
    def convert_to_uuids(id_list):
        if not id_list:
            return []
        try:
            return [uuid.UUID(id_str) for id_str in id_list if id_str]
        except (ValueError, AttributeError):
            return []
    
    brand_ids = convert_to_uuids(brand_ids)
    voltage_ids = convert_to_uuids(voltage_ids)
    platform_ids = convert_to_uuids(platform_ids)
    status_ids = convert_to_uuids(status_ids)
    
    # Start with all products
    products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    # Apply filters
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        products = products.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        products = products.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        products = products.filter(batteryplatforms__id__in=platform_ids)
    
    # Category filtering with hierarchy support
    products = get_category_hierarchy_filters(products, category_level1, category_level2, category_level3, 'products')
    
    if status_ids:
        products = products.filter(status__id__in=status_ids)
    
    # Date range filtering
    if release_date_from:
        products = products.filter(releasedate__gte=release_date_from)
    
    if release_date_to:
        products = products.filter(releasedate__lte=release_date_to)
    
    # Apply sorting
    if sort == 'brand':
        if sort_direction == 'desc':
            products = products.order_by('-brand__name', 'name')
        else:
            products = products.order_by('brand__name', 'name')
    elif sort == 'voltage':
        if sort_direction == 'desc':
            products = products.order_by('-batteryvoltages__value', 'name')
        else:
            products = products.order_by('batteryvoltages__value', 'name')
    elif sort == 'release_date':
        if sort_direction == 'desc':
            products = products.order_by('-releasedate', 'name')
        else:
            products = products.order_by('releasedate', 'name')
    else:
        # Default: use category sortorder to deprioritize ProPEX, draw studs, etc.
        if sort_direction == 'desc':
            products = products.order_by('-itemcategories__parent__parent__sortorder', '-itemcategories__parent__sortorder', '-itemcategories__sortorder', '-name').distinct()
        else:
            products = products.order_by('itemcategories__parent__parent__sortorder', 'itemcategories__parent__sortorder', 'itemcategories__sortorder', 'name').distinct()
    
    # Paginate
    paginator = Paginator(products, 24)
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # Get filter options that would actually change the result count
    # Start with all products for each filter type, then apply other filters
    
    # For brands: apply all filters except brand
    brand_base_products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    if search:
        brand_base_products = brand_base_products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if voltage_ids:
        brand_base_products = brand_base_products.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        brand_base_products = brand_base_products.filter(batteryplatforms__id__in=platform_ids)
    
    if status_ids:
        brand_base_products = brand_base_products.filter(status__id__in=status_ids)
    
    if release_date_from:
        brand_base_products = brand_base_products.filter(releasedate__gte=release_date_from)
    
    if release_date_to:
        brand_base_products = brand_base_products.filter(releasedate__lte=release_date_to)
    
    # Apply category filters to brand base
    brand_base_products = get_category_hierarchy_filters(brand_base_products, category_level1, category_level2, category_level3, 'products')
    
    # For voltages: apply all filters except voltage
    voltage_base_products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    if search:
        voltage_base_products = voltage_base_products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        voltage_base_products = voltage_base_products.filter(brand__id__in=brand_ids)
    
    if platform_ids:
        voltage_base_products = voltage_base_products.filter(batteryplatforms__id__in=platform_ids)
    
    if status_ids:
        voltage_base_products = voltage_base_products.filter(status__id__in=status_ids)
    
    if release_date_from:
        voltage_base_products = voltage_base_products.filter(releasedate__gte=release_date_from)
    
    if release_date_to:
        voltage_base_products = voltage_base_products.filter(releasedate__lte=release_date_to)
    
    # Apply category filters to voltage base
    voltage_base_products = get_category_hierarchy_filters(voltage_base_products, category_level1, category_level2, category_level3, 'products')
    
    # For platforms: apply all filters except platform
    platform_base_products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    if search:
        platform_base_products = platform_base_products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        platform_base_products = platform_base_products.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        platform_base_products = platform_base_products.filter(batteryvoltages__id__in=voltage_ids)
    
    if status_ids:
        platform_base_products = platform_base_products.filter(status__id__in=status_ids)
    
    if release_date_from:
        platform_base_products = platform_base_products.filter(releasedate__gte=release_date_from)
    
    if release_date_to:
        platform_base_products = platform_base_products.filter(releasedate__lte=release_date_to)
    
    # Apply category filters to platform base
    platform_base_products = get_category_hierarchy_filters(platform_base_products, category_level1, category_level2, category_level3, 'products')
    
    # For statuses: apply all filters except status
    status_base_products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    if search:
        status_base_products = status_base_products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        status_base_products = status_base_products.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        status_base_products = status_base_products.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        status_base_products = status_base_products.filter(batteryplatforms__id__in=platform_ids)
    
    if release_date_from:
        status_base_products = status_base_products.filter(releasedate__gte=release_date_from)
    
    if release_date_to:
        status_base_products = status_base_products.filter(releasedate__lte=release_date_to)
    
    # Apply category filters to status base
    status_base_products = get_category_hierarchy_filters(status_base_products, category_level1, category_level2, category_level3, 'products')
    
    # Get filter options based on their respective base products
    brands = Brands.objects.filter(products__in=brand_base_products).distinct().order_by('name')
    voltages = BatteryVoltages.objects.filter(products__in=voltage_base_products).distinct().order_by('value')
    platforms = BatteryPlatforms.objects.filter(products__in=platform_base_products).distinct().order_by('name')
    statuses = Statuses.objects.filter(products__in=status_base_products).distinct().order_by('name')
    
    # Get categories using utility function - use brand_base_products as it has all non-category filters applied
    category_data = build_category_hierarchy_data(brand_base_products, category_level1, category_level2, category_level3, 'products')
    level1_categories = category_data['level1_categories']
    level2_categories = category_data['level2_categories']
    level3_categories = category_data['level3_categories']
    level2_categories_with_parent = category_data['level2_categories_with_parent']
    level3_categories_with_parent = category_data['level3_categories_with_parent']
    
    # Calculate filter counts
    filter_counts = {
        'brands': {
            'selected': len(brand_ids),
            'total': brands.count()
        },
        'voltages': {
            'selected': len(voltage_ids),
            'total': voltages.count()
        },
        'platforms': {
            'selected': len(platform_ids),
            'total': platforms.count()
        },
        'statuses': {
            'selected': len(status_ids),
            'total': statuses.count()
        }
    }
    
    context = {
        'products': page_obj,
        'brands': brands,
        'voltages': voltages,
        'platforms': platforms,
        'statuses': statuses,
        'level1_categories': level1_categories,
        'level2_categories': level2_categories,
        'level3_categories': level3_categories,
        'level2_categories_with_parent': level2_categories_with_parent,
        'level3_categories_with_parent': level3_categories_with_parent,
        'filter_counts': filter_counts,
        'current_filters': {
            'search': search,
            'brand': brand,
            'voltage': voltage,
            'platform': platform,
            'category_level1': category_level1,
            'category_level2': category_level2,
            'category_level3': category_level3,
            'status': status,
            'release_date_from': release_date_from,
            'release_date_to': release_date_to,
            'sort': sort,
            'sort_direction': sort_direction,
        },
        'selected_brand_ids': brand_ids,
        'selected_voltage_ids': voltage_ids,
        'selected_platform_ids': platform_ids,
        'selected_status_ids': status_ids,
    }
    
    return render(request, 'frontend/index.html', context)

def product_detail(request, product_id):
    """Product detail view"""
    product = get_object_or_404(Products, id=product_id)
    
    # Get sorting parameters
    sort = request.GET.get('sort', 'name')
    sort_direction = request.GET.get('sort_direction', 'asc')
    
    # Get product components with prefetched data
    product_components = product.productcomponents_set.select_related(
        'component__brand'
    ).prefetch_related(
        'component__itemcategories__attributes',
        'component__componentattributes_set__attribute'
    ).all()
    
    # For each component, look up products with the same SKU and brand
    component_products = {}
    for product_component in product_components:
        component = product_component.component
        if component.sku and component.brand:
            # Find products with same SKU and brand as the component
            matching_products = Products.objects.filter(
                sku=component.sku,
                brand=component.brand
            ).exclude(id=product.id)  # Exclude current product
            
            if matching_products.exists():
                # Get the first matching product's image
                first_product = matching_products.first()
                if first_product.image:
                    component_products[component.id] = first_product.image
                elif first_product.productimages_set.exists():
                    component_products[component.id] = first_product.productimages_set.first().image
    
    # Apply sorting to product components
    if sort == 'quantity':
        if sort_direction == 'desc':
            product_components = product_components.order_by('-quantity', 'component__name')
        else:
            product_components = product_components.order_by('quantity', 'component__name')
    elif sort == 'sku':
        if sort_direction == 'desc':
            product_components = product_components.order_by('-component__sku', 'component__name')
        else:
            product_components = product_components.order_by('component__sku', 'component__name')
    else:  # Default: sort by component name
        if sort_direction == 'desc':
            product_components = product_components.order_by('-component__name')
        else:
            product_components = product_components.order_by('component__name')
    
    # Group components by their primary category and get dynamic columns
    # Order: power_tools first, then batteries, then chargers, then accessories, then other
    component_groups = {
        'power_tools': {'components': [], 'columns': []},
        'batteries': {'components': [], 'columns': []},
        'chargers': {'components': [], 'columns': []},
        'accessories': {'components': [], 'columns': []},
        'other': {'components': [], 'columns': []}
    }
    
    # Categorize components and get their data
    for product_component in product_components:
        component = product_component.component
        
        # Determine component category based on item categories
        component_category = 'other'  # default
        for category in component.itemcategories.all():
            category_name = category.name.lower()
            if category_name == 'batteries':
                component_category = 'batteries'
                break
            elif category_name == 'chargers':
                component_category = 'chargers'
                break
            elif any(tool in category_name for tool in ['drill', 'saw', 'driver', 'impact', 'grinder', 'tool']):
                component_category = 'power_tools'
                break
            elif any(acc in category_name for acc in ['accessory', 'case', 'bag', 'bit', 'blade']):
                component_category = 'accessories'
                break
        
        component_data = {
            'product_component': product_component
        }
        
        component_groups[component_category]['components'].append(component_data)
    
    # Get dynamic columns for each group based on item category attributes
    for group_name, group_data in component_groups.items():
        if group_data['components']:
            # Get all unique item categories for this group
            group_categories = set()
            for component_data in group_data['components']:
                component = component_data['product_component'].component
                for category in component.itemcategories.all():
                    group_categories.add(category)
            
            # Get all attributes for these categories
            group_attributes = set()
            for category in group_categories:
                for attribute in category.attributes.all():
                    group_attributes.add(attribute)
            
            # Convert to list and sort by name
            group_data['columns'] = sorted(list(group_attributes), key=lambda x: x.name)
    
    # Remove empty groups
    component_groups = {k: v for k, v in component_groups.items() if v['components']}
    
    context = {
        'product': product,
        'component_products': component_products,
        'component_groups': component_groups,
        'current_filters': {
            'sort': sort,
            'sort_direction': sort_direction,
        },
    }
    
    return render(request, 'frontend/product_detail.html', context)

def components_index(request):
    """Component catalog with filtering and pagination"""
    # Get filter parameters
    search = request.GET.get('search', '')
    brand = request.GET.get('brand', '')
    voltage = request.GET.get('voltage', '')
    platform = request.GET.get('platform', '')
    category_level1 = request.GET.get('category_level1', '')
    category_level2 = request.GET.get('category_level2', '')
    category_level3 = request.GET.get('category_level3', '')
    product_line = request.GET.get('product_line', '')
    listing_type = request.GET.get('listing_type', '')
    sort = request.GET.get('sort', 'name')
    sort_direction = request.GET.get('sort_direction', 'asc')
    page = int(request.GET.get('page', 1))
    
    # Parse multi-select values
    brand_ids = request.GET.getlist('brand')
    voltage_ids = request.GET.getlist('voltage')
    platform_ids = request.GET.getlist('platform')
    product_line_ids = request.GET.getlist('product_line')
    listing_type_ids = request.GET.getlist('listing_type')
    
    # Handle comma-separated values if no individual values
    if not brand_ids and brand:
        brand_ids = [x.strip() for x in brand.split(',')]
    if not voltage_ids and voltage:
        voltage_ids = [x.strip() for x in voltage.split(',')]
    if not platform_ids and platform:
        platform_ids = [x.strip() for x in platform.split(',')]
    if not product_line_ids and product_line:
        product_line_ids = [x.strip() for x in product_line.split(',')]
    if not listing_type_ids and listing_type:
        listing_type_ids = [x.strip() for x in listing_type.split(',')]
    
    # Convert string IDs to UUIDs for database filtering
    def convert_to_uuids(id_list):
        if not id_list:
            return []
        try:
            return [uuid.UUID(id_str) for id_str in id_list if id_str]
        except (ValueError, AttributeError):
            return []
    
    brand_ids = convert_to_uuids(brand_ids)
    voltage_ids = convert_to_uuids(voltage_ids)
    platform_ids = convert_to_uuids(platform_ids)
    product_line_ids = convert_to_uuids(product_line_ids)
    listing_type_ids = convert_to_uuids(listing_type_ids)
    
    # Parse attribute filters - get all attribute parameters
    attribute_filters = {}
    feature_filters = {}
    for key, value in request.GET.items():
        if key.startswith('attr_'):
            attr_id = key.replace('attr_', '')
            attr_values = request.GET.getlist(key)
            if attr_values:
                attribute_filters[attr_id] = attr_values
        elif key.startswith('feature_'):
            feature_id = key.replace('feature_', '')
            feature_values = request.GET.getlist(key)
            if feature_values:
                feature_filters[feature_id] = feature_values
    
    # Start with all components
    components = Components.objects.select_related('brand', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories', 'productlines'
    ).all()
    
    # Apply filters
    if search:
        components = components.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        components = components.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        components = components.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        components = components.filter(batteryplatforms__id__in=platform_ids)
    
    # Category filtering with hierarchy support
    components = get_category_hierarchy_filters(components, category_level1, category_level2, category_level3, 'components')
    
    if product_line_ids:
        components = components.filter(productlines__id__in=product_line_ids)
    
    if listing_type_ids:
        components = components.filter(listingtype__in=listing_type_ids)
    
    # Apply attribute filters
    if attribute_filters:
        for attr_id, attr_values in attribute_filters.items():
            components = components.filter(
                componentattributes__attribute_id=attr_id,
                componentattributes__value__in=attr_values
            ).distinct()
    
    # Apply feature filters (case-insensitive)
    if feature_filters:
        for feature_id, feature_values in feature_filters.items():
            # Convert feature values to lowercase for case-insensitive matching
            lowercase_values = [val.lower() for val in feature_values]
            components = components.filter(
                componentattributes__attribute_id=feature_id,
                componentattributes__value__in=lowercase_values
            ).distinct()
    
    # Apply sorting
    if sort == 'brand':
        if sort_direction == 'desc':
            components = components.order_by('-brand__name', 'name')
        else:
            components = components.order_by('brand__name', 'name')
    elif sort == 'voltage':
        if sort_direction == 'desc':
            components = components.order_by('-batteryvoltages__value', 'name')
        else:
            components = components.order_by('batteryvoltages__value', 'name')
    elif sort == 'fair_price':
        # Extract fair_price from JSONField and handle nulls
        components = components.annotate(
            fair_price_value=Case(
                When(fair_price_narrative__fair_price__isnull=False,
                     then=Cast(F('fair_price_narrative__fair_price'), FloatField())),
                default=Value(None),
                output_field=FloatField()
            )
        )
        if sort_direction == 'desc':
            components = components.order_by(F('fair_price_value').desc(nulls_last=True), 'name')
        else:
            components = components.order_by(F('fair_price_value').asc(nulls_last=True), 'name')
    else:
        # Default: use category sortorder to deprioritize ProPEX, draw studs, etc.
        if sort_direction == 'desc':
            components = components.order_by('-itemcategories__parent__parent__sortorder', '-itemcategories__parent__sortorder', '-itemcategories__sortorder', '-name').distinct()
        else:
            components = components.order_by('itemcategories__parent__parent__sortorder', 'itemcategories__parent__sortorder', 'itemcategories__sortorder', 'name').distinct()
    
    # Paginate
    paginator = Paginator(components, 24)
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # Get filter options - filter by non-category filters to avoid circular dependency
    non_category_components = Components.objects.select_related('brand', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories', 'productlines'
    ).all()
    
    # Apply non-category filters
    if search:
        non_category_components = non_category_components.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        non_category_components = non_category_components.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        non_category_components = non_category_components.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        non_category_components = non_category_components.filter(batteryplatforms__id__in=platform_ids)
    
    if product_line_ids:
        non_category_components = non_category_components.filter(productlines__id__in=product_line_ids)
    
    if listing_type_ids:
        non_category_components = non_category_components.filter(listingtype__in=listing_type_ids)
    
    # Apply attribute filters to non-category components
    if attribute_filters:
        for attr_id, attr_values in attribute_filters.items():
            non_category_components = non_category_components.filter(
                componentattributes__attribute_id=attr_id,
                componentattributes__value__in=attr_values
            ).distinct()
    
    # Apply feature filters to non-category components
    if feature_filters:
        for feature_id, feature_values in feature_filters.items():
            non_category_components = non_category_components.filter(
                componentattributes__attribute_id=feature_id,
                componentattributes__value__in=feature_values
            ).distinct()
    
    # Get all available filter options based on non-category filtered components
    brands = Brands.objects.filter(components__in=non_category_components).distinct().order_by('name')
    voltages = BatteryVoltages.objects.filter(components__in=non_category_components).distinct().order_by('value')
    # Get platforms - try filtered first, fallback to all if empty
    platforms = BatteryPlatforms.objects.filter(components__in=non_category_components).distinct().order_by('name')
    if not platforms.exists():
        # Fallback: show all platforms if none found in filtered results
        platforms = BatteryPlatforms.objects.all().order_by('name')
    product_lines = ProductLines.objects.filter(components__in=non_category_components).distinct().order_by('name')
    
    # Get categories using utility function
    category_data = build_category_hierarchy_data(non_category_components, category_level1, category_level2, category_level3, 'components')
    level1_categories = category_data['level1_categories']
    level2_categories = category_data['level2_categories']
    level3_categories = category_data['level3_categories']
    level2_categories_with_parent = category_data['level2_categories_with_parent']
    level3_categories_with_parent = category_data['level3_categories_with_parent']
    
    # Get attributes with their values for filtering - only from filtered components
    attributes_with_values = ComponentAttributes.objects.filter(
        component__in=non_category_components
    ).values('attribute__id', 'attribute__name', 'attribute__unit', 'value').distinct().order_by('attribute__name', 'value')
    
    # Group attributes by attribute
    attributes_dict = {}
    for attr_data in attributes_with_values:
        attr_id = str(attr_data['attribute__id'])
        if attr_id not in attributes_dict:
            attributes_dict[attr_id] = {
                'id': attr_id,
                'name': attr_data['attribute__name'],
                'unit': attr_data['attribute__unit'],
                'values': []
            }
        if attr_data['value']:
            attributes_dict[attr_id]['values'].append(attr_data['value'])
        else:
            attributes_dict[attr_id]['values'].append('No')
    
    # Sort values for each attribute and separate features
    features = []
    regular_attributes = []
    
    for attr_data in attributes_dict.values():
        attr_data['values'].sort()
        
        # Check if this is a feature (boolean attributes with yes/no values)
        unique_values = set(attr_data['values'])
        # Convert to lowercase for case-insensitive comparison
        unique_values_lower = {str(val).lower().strip() for val in unique_values if val}
        
        # A feature is one that only has "yes"/"no" values (case-insensitive)
        if (not unique_values_lower or 
            unique_values_lower == {'yes'} or 
            unique_values_lower == {'no'} or
            unique_values_lower.issubset({'yes', 'no'})):
            features.append(attr_data)
        else:
            regular_attributes.append(attr_data)
    
    # Calculate filter counts
    filter_counts = {
        'brands': {
            'selected': len(brand_ids),
            'total': brands.count()
        },
        'voltages': {
            'selected': len(voltage_ids),
            'total': voltages.count()
        },
        'platforms': {
            'selected': len(platform_ids),
            'total': platforms.count()
        },
        'product_lines': {
            'selected': len(product_line_ids),
            'total': product_lines.count()
        }
    }
    
    # Get site settings for fair price feature
    site_settings = SiteSettings.get_settings()
    
    context = {
        'components': page_obj,
        'brands': brands,
        'voltages': voltages,
        'platforms': platforms,
        'product_lines': product_lines,
        'level1_categories': level1_categories,
        'level2_categories': level2_categories,
        'level3_categories': level3_categories,
        'level2_categories_with_parent': level2_categories_with_parent,
        'level3_categories_with_parent': level3_categories_with_parent,
        'features': features,
        'attributes': regular_attributes,
        'filter_counts': filter_counts,
        'current_filters': {
            'search': search,
            'brand': brand,
            'voltage': voltage,
            'platform': platform,
            'category_level1': category_level1,
            'category_level2': category_level2,
            'category_level3': category_level3,
            'product_line': product_line,
            'listing_type': listing_type,
            'sort': sort,
            'sort_direction': sort_direction,
        },
        'selected_brand_ids': brand_ids,
        'selected_voltage_ids': voltage_ids,
        'selected_platform_ids': platform_ids,
        'selected_product_line_ids': product_line_ids,
        'selected_attribute_filters': attribute_filters,
        'selected_feature_filters': feature_filters,
        'show_fair_price': site_settings.show_fair_price_feature,
    }
    
    return render(request, 'frontend/components_index.html', context)

def component_detail(request, component_id):
    """Component detail view"""
    component = get_object_or_404(Components, id=component_id)
    
    # Get all component attributes
    component_attributes = ComponentAttributes.objects.filter(component=component).select_related('attribute')
    
    # Get category-designated attributes from component's ItemCategories
    category_attributes = Attributes.objects.filter(
        itemcategories__in=component.itemcategories.all()
    ).distinct()
    
    # Separate important vs additional attributes
    # Important attributes are those that are designated for the component's categories
    important_attributes = component_attributes.filter(attribute__in=category_attributes)
    # Additional attributes are everything else
    additional_attributes = component_attributes.exclude(attribute__in=category_attributes)
    
    # Get products that use this component
    product_components = ProductComponents.objects.filter(component=component).select_related('product').prefetch_related('product__productimages_set')
    
    # Get site settings for fair price feature
    site_settings = SiteSettings.get_settings()
    
    context = {
        'component': component,
        'important_attributes': important_attributes,
        'additional_attributes': additional_attributes,
        'product_components': product_components,
        'show_fair_price': site_settings.show_fair_price_feature,
    }
    
    return render(request, 'frontend/component_detail.html', context)

def browse_flagship(request):
    """Browse flagship products organized by category and brand"""
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    brand_filter = request.GET.get('brand', '')
    sort = request.GET.get('sort', 'name')
    sort_direction = request.GET.get('sort_direction', 'asc')
    
    # Query flagship products by SKU list
    if FLAGSHIP_PRODUCT_SKUS:
        flagship_products = Products.objects.filter(
            sku__in=FLAGSHIP_PRODUCT_SKUS
        ).select_related('brand').prefetch_related('itemcategories', 'productimages_set')
    else:
        flagship_products = Products.objects.none()
    
    # Apply category filter if specified
    if category_filter:
        flagship_products = flagship_products.filter(itemcategories__id=category_filter)
    
    # Apply brand filter if specified
    if brand_filter:
        flagship_products = flagship_products.filter(brand__id=brand_filter)
    
    # Apply sorting
    if sort == 'brand':
        if sort_direction == 'desc':
            flagship_products = flagship_products.order_by('-brand__name', 'name')
        else:
            flagship_products = flagship_products.order_by('brand__name', 'name')
    elif sort == 'voltage':
        if sort_direction == 'desc':
            flagship_products = flagship_products.order_by('-batteryvoltages__value', 'name')
        else:
            flagship_products = flagship_products.order_by('batteryvoltages__value', 'name')
    elif sort == 'release_date':
        if sort_direction == 'desc':
            flagship_products = flagship_products.order_by('-releasedate', 'name')
        else:
            flagship_products = flagship_products.order_by('releasedate', 'name')
    else:
        # Default: sort by name
        if sort_direction == 'desc':
            flagship_products = flagship_products.order_by('-name')
        else:
            flagship_products = flagship_products.order_by('name')
    
    # Organize products by Level 1 category
    organized_products = {}
    for product in flagship_products:
        # Get the primary Level 1 category for this product
        level1_category = None
        for category in product.itemcategories.all():
            if category.level == 1:
                level1_category = category
                break
            elif category.level == 2 and category.parent and category.parent.level == 1:
                level1_category = category.parent
                break
            elif category.level == 3 and category.parent and category.parent.parent and category.parent.parent.level == 1:
                level1_category = category.parent.parent
                break
        
        if level1_category:
            category_name = level1_category.name
            if category_name not in organized_products:
                organized_products[category_name] = {
                    'category': level1_category,
                    'brands': {}
                }
            
            brand_name = product.brand.name if product.brand else 'Unknown Brand'
            if brand_name not in organized_products[category_name]['brands']:
                organized_products[category_name]['brands'][brand_name] = []
            
            organized_products[category_name]['brands'][brand_name].append(product)
    
    # Get all Level 1 categories for navigation
    level1_categories = ItemCategories.objects.filter(level=1).order_by('sortorder', 'name')
    
    # Get all brands for navigation
    brands = Brands.objects.filter(products__in=flagship_products).distinct().order_by('name')
    
    context = {
        'organized_products': organized_products,
        'level1_categories': level1_categories,
        'brands': brands,
        'current_category': category_filter,
        'current_brand': brand_filter,
        'has_products': len(FLAGSHIP_PRODUCT_SKUS) > 0,
        'current_filters': {
            'sort': sort,
            'sort_direction': sort_direction,
        },
    }
    
    return render(request, 'frontend/browse.html', context)

def home(request):
    """Home page with site overview and statistics"""
    # Get basic statistics for the home page
    total_products = Products.objects.count()
    total_components = Components.objects.count()
    total_brands = Brands.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    total_categories = ItemCategories.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    
    # Get flagship products preview (first 4 from FLAGSHIP_PRODUCT_SKUS)
    flagship_preview = []
    if FLAGSHIP_PRODUCT_SKUS:
        flagship_preview = Products.objects.filter(
            sku__in=FLAGSHIP_PRODUCT_SKUS[:4]
        ).select_related('brand').prefetch_related('itemcategories', 'productimages_set')
    
    # Get recent products (latest 3 by release date)
    recent_products = Products.objects.select_related('brand').prefetch_related('productimages_set').order_by('-releasedate')[:3]
    
    # Get recent components (latest 3)
    recent_components = Components.objects.select_related('brand').order_by('-id')[:3]
    
    context = {
        'total_products': total_products,
        'total_components': total_components,
        'total_brands': total_brands,
        'total_categories': total_categories,
        'flagship_preview': flagship_preview,
        'recent_products': recent_products,
        'recent_components': recent_components,
        'has_flagship_products': len(FLAGSHIP_PRODUCT_SKUS) > 0,
    }
    
    return render(request, 'frontend/home.html', context)

def about(request):
    """About page with information about the database"""
    return render(request, 'frontend/about.html')

def contact(request):
    """Contact page with contact information and form"""
    return render(request, 'frontend/contact.html')

def learning_index(request):
    """Learning articles index page"""
    articles = LearningArticle.objects.filter(is_published=True).prefetch_related('tags')
    
    # Get search parameter
    search = request.GET.get('search', '')
    if search:
        articles = articles.filter(
            Q(title__icontains=search) | 
            Q(summary__icontains=search) |
            Q(content__icontains=search)
        )
    
    # Get tag filter parameter
    tag_slug = request.GET.get('tag', '')
    if tag_slug:
        articles = articles.filter(tags__slug=tag_slug)
    
    # Get all available tags with article counts
    all_tags = Tag.objects.annotate(
        article_count=Count('articles', filter=Q(articles__is_published=True))
    ).filter(article_count__gt=0).order_by('name')
    
    # Paginate articles
    paginator = Paginator(articles, 12)
    page = int(request.GET.get('page', 1))
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    context = {
        'articles': page_obj,
        'search': search,
        'tag_slug': tag_slug,
        'all_tags': all_tags,
    }
    
    return render(request, 'frontend/learning_index.html', context)

def learning_detail(request, slug):
    """Learning article detail page"""
    article = get_object_or_404(LearningArticle, slug=slug, is_published=True)
    
    # Get related articles - prefer articles with same tags, then other published articles
    related_articles = LearningArticle.objects.filter(
        is_published=True
    ).exclude(id=article.id)
    
    # If article has tags, try to find articles with same tags first
    if article.tags.exists():
        same_tag_articles = related_articles.filter(tags__in=article.tags.all()).distinct()[:3]
        if same_tag_articles.count() >= 3:
            related_articles = same_tag_articles
        else:
            # Fill remaining slots with other articles
            other_articles = related_articles.exclude(tags__in=article.tags.all())[:3-same_tag_articles.count()]
            related_articles = list(same_tag_articles) + list(other_articles)
    else:
        related_articles = related_articles[:3]
    
    context = {
        'article': article,
        'related_articles': related_articles,
    }
    
    return render(request, 'frontend/learning_detail.html', context)

# API Endpoints for Dynamic Features

def api_search_suggestions(request):
    """API endpoint for search suggestions with autocomplete"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    # Search products
    products = Products.objects.filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    ).select_related('brand')[:5]
    
    for product in products:
        suggestions.append({
            'text': product.name,
            'type': 'Product',
            'url': f'/product/{product.id}/',
            'brand': product.brand.name if product.brand else '',
            'sku': product.sku or ''
        })
    
    # Search components
    components = Components.objects.filter(
        Q(name__icontains=query) | Q(sku__icontains=query)
    ).select_related('brand')[:5]
    
    for component in components:
        suggestions.append({
            'text': component.name,
            'type': 'Component',
            'url': f'/components/{component.id}/',
            'brand': component.brand.name if component.brand else '',
            'sku': component.sku or ''
        })
    
    # Search brands
    brands = Brands.objects.filter(name__icontains=query)[:3]
    
    for brand in brands:
        suggestions.append({
            'text': brand.name,
            'type': 'Brand',
            'url': f'/products/?brand={brand.id}',
            'brand': '',
            'sku': ''
        })
    
    return JsonResponse({'suggestions': suggestions})

def api_filter_options(request):
    """API endpoint for dynamic filter options based on current selections"""
    # Get current filter parameters
    search = request.GET.get('search', '')
    brand_ids = request.GET.getlist('brand')
    voltage_ids = request.GET.getlist('voltage')
    platform_ids = request.GET.getlist('platform')
    category_level1 = request.GET.get('category_level1', '')
    category_level2 = request.GET.get('category_level2', '')
    category_level3 = request.GET.get('category_level3', '')
    
    # Convert string IDs to UUIDs for database filtering
    def convert_to_uuids(id_list):
        if not id_list:
            return []
        try:
            return [uuid.UUID(id_str) for id_str in id_list if id_str]
        except (ValueError, AttributeError):
            return []
    
    brand_ids = convert_to_uuids(brand_ids)
    voltage_ids = convert_to_uuids(voltage_ids)
    platform_ids = convert_to_uuids(platform_ids)
    
    # Start with all products
    products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    # Apply non-category filters
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        products = products.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        products = products.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        products = products.filter(batteryplatforms__id__in=platform_ids)
    
    # Get available filter options
    brands = Brands.objects.filter(products__in=products).distinct().order_by('name')
    voltages = BatteryVoltages.objects.filter(products__in=products).distinct().order_by('value')
    platforms = BatteryPlatforms.objects.filter(products__in=products).distinct().order_by('name')
    
    # Get categories based on current selection
    if category_level1:
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            parent=category_level1,
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        
        if category_level2:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent=category_level2,
                products__in=products
            ).distinct().order_by('sortorder', 'name')
        else:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent__parent=category_level1,
                products__in=products
            ).distinct().order_by('sortorder', 'name')
    else:
        level1_categories = ItemCategories.objects.filter(
            level=1, 
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        level3_categories = ItemCategories.objects.filter(
            level=3, 
            products__in=products
        ).distinct().order_by('sortorder', 'name')
    
    return JsonResponse({
        'brands': [{'id': b.id, 'name': b.name} for b in brands],
        'voltages': [{'id': v.id, 'value': v.value} for v in voltages],
        'platforms': [{'id': p.id, 'name': p.name} for p in platforms],
        'level1_categories': [{'id': c.id, 'name': c.name} for c in level1_categories] if 'level1_categories' in locals() else [],
        'level2_categories': [{'id': c.id, 'name': c.name, 'parent': c.parent} for c in level2_categories],
        'level3_categories': [{'id': c.id, 'name': c.name, 'parent': c.parent} for c in level3_categories],
    })

def api_quick_info(request, item_id):
    """API endpoint for quick product/component info for tooltips"""
    item_type = request.GET.get('type', 'product')
    
    if item_type == 'product':
        try:
            product = Products.objects.select_related('brand', 'status').prefetch_related(
                'batteryplatforms', 'productcomponents_set__component'
            ).get(id=item_id)
            
            # Get battery platforms
            battery_platforms = [platform.name for platform in product.batteryplatforms.all()]
            
            # Get components list
            components = []
            for product_component in product.productcomponents_set.all():
                component = product_component.component
                components.append({
                    'name': component.name,
                    'quantity': product_component.quantity,
                    'sku': component.sku or '',
                    'url': f'/components/{component.id}/'
                })
            
            return JsonResponse({
                'name': product.name,
                'brand': product.brand.name if product.brand else '',
                'sku': product.sku or '',
                'status': product.status.name if product.status else '',
                'image': product.image or '',
                'description': product.description or '',
                'battery_platforms': battery_platforms,
                'components': components,
                'url': f'/product/{product.id}/'
            })
        except Products.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
    
    elif item_type == 'component':
        try:
            component = Components.objects.select_related('brand').prefetch_related(
                'itemcategories__attributes', 'componentattributes_set__attribute'
            ).get(id=item_id)
            
            # Get category-designated attributes (key attributes)
            category_attributes = Attributes.objects.filter(
                itemcategories__in=component.itemcategories.all()
            ).distinct()
            
            # Get component attributes that are designated by categories
            important_attributes = ComponentAttributes.objects.filter(
                component=component,
                attribute__in=category_attributes
            ).select_related('attribute')
            
            key_attributes = []
            for attr in important_attributes:
                key_attributes.append({
                    'name': attr.attribute.name,
                    'value': attr.value or 'N/A',
                    'unit': attr.attribute.unit or ''
                })
            
            return JsonResponse({
                'name': component.name,
                'brand': component.brand.name if component.brand else '',
                'sku': component.sku or '',
                'image': component.image or '',
                'description': component.description or '',
                'key_attributes': key_attributes,
                'url': f'/components/{component.id}/'
            })
        except Components.DoesNotExist:
            return JsonResponse({'error': 'Component not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid item type'}, status=400)

def api_compare_components(request):
    """API endpoint for component comparison data"""
    component_ids = request.GET.get('component_ids', '')
    if not component_ids:
        return JsonResponse({'error': 'No component IDs provided'}, status=400)
    
    try:
        # Parse component IDs
        component_id_list = [id.strip() for id in component_ids.split(',') if id.strip()]
        if len(component_id_list) > 4:
            return JsonResponse({'error': 'Maximum 4 components can be compared'}, status=400)
        
        # Query components with all related data
        components = Components.objects.filter(
            id__in=component_id_list
        ).select_related('brand', 'listingtype').prefetch_related(
            'batteryvoltages', 'batteryplatforms', 'itemcategories', 'productlines',
            'componentattributes_set__attribute'
        ).order_by('name')
        
        if not components.exists():
            return JsonResponse({'error': 'No components found'}, status=404)
        
        # Get site settings for fair price feature
        site_settings = SiteSettings.get_settings()
        
        comparison_data = {
            'components': [],
            'common_attributes': [],
            'all_attributes': [],
            'show_fair_price': site_settings.show_fair_price_feature
        }
        
        # Process each component
        for component in components:
            # Get category-designated attributes (important attributes)
            category_attributes = Attributes.objects.filter(
                itemcategories__in=component.itemcategories.all()
            ).distinct()
            
            # Get component attributes
            component_attrs = component.componentattributes_set.select_related('attribute').all()
            
            # Separate important vs additional attributes
            important_attrs = component_attrs.filter(attribute__in=category_attributes)
            additional_attrs = component_attrs.exclude(attribute__in=category_attributes)
            
            # Build component data
            component_data = {
                'id': str(component.id),
                'name': component.name,
                'description': component.description or '',
                'sku': component.sku or '',
                'brand': component.brand.name if component.brand else '',
                'image': component.image or '',
                'voltage': [str(v.value) for v in component.batteryvoltages.all()],
                'platform': [p.name for p in component.batteryplatforms.all()],
                'product_lines': [pl.name for pl in component.productlines.all()],
                'categories': [c.name for c in component.itemcategories.all()],
                'important_attributes': {},
                'additional_attributes': {},
                'fair_price': None
            }
            
            # Add important attributes
            for attr in important_attrs:
                component_data['important_attributes'][attr.attribute.name] = {
                    'value': attr.value or 'N/A',
                    'unit': attr.attribute.unit or ''
                }
            
            # Add additional attributes
            for attr in additional_attrs:
                component_data['additional_attributes'][attr.attribute.name] = {
                    'value': attr.value or 'N/A',
                    'unit': attr.attribute.unit or ''
                }
            
            # Add fair price data if enabled
            if site_settings.show_fair_price_feature:
                try:
                    if hasattr(component, 'fair_price_narrative') and component.fair_price_narrative and component.fair_price_narrative.get('fair_price'):
                        component_data['fair_price'] = {
                            'price': component.fair_price_narrative.get('fair_price'),
                            'reasoning': component.fair_price_narrative.get('reasoning', ''),
                            'pros': component.fair_price_narrative.get('pros', []),
                            'cons': component.fair_price_narrative.get('cons', []),
                            'market_notes': component.fair_price_narrative.get('market_notes', '')
                        }
                    else:
                        # Always add fair_price key when feature is enabled, even if no data
                        component_data['fair_price'] = None
                except Exception as e:
                    component_data['fair_price'] = None
            
            comparison_data['components'].append(component_data)
        
        # Find all attributes across all components (for detailed comparison)
        if comparison_data['components']:
            # Get all important attribute names from any component
            all_important_attrs = set()
            for comp in comparison_data['components']:
                all_important_attrs.update(comp['important_attributes'].keys())
            
            # Get all additional attribute names from any component
            all_additional_attrs = set()
            for comp in comparison_data['components']:
                all_additional_attrs.update(comp['additional_attributes'].keys())
            
            # Build all important attributes list with units
            for attr_name in sorted(all_important_attrs):
                # Get unit from first component that has this attribute
                unit = ''
                for comp in comparison_data['components']:
                    if attr_name in comp['important_attributes']:
                        unit = comp['important_attributes'][attr_name]['unit']
                        break
                comparison_data['common_attributes'].append({
                    'name': attr_name,
                    'unit': unit,
                    'type': 'important'
                })
            
            # Build all additional attributes list with units
            for attr_name in sorted(all_additional_attrs):
                # Get unit from first component that has this attribute
                unit = ''
                for comp in comparison_data['components']:
                    if attr_name in comp['additional_attributes']:
                        unit = comp['additional_attributes'][attr_name]['unit']
                        break
                comparison_data['common_attributes'].append({
                    'name': attr_name,
                    'unit': unit,
                    'type': 'additional'
                })
            
            # Build all attributes list (for showing all available attributes)
            all_attrs = sorted(all_important_attrs | all_additional_attrs)
            for attr_name in all_attrs:
                # Get unit from first component that has this attribute
                unit = ''
                attr_type = 'additional'
                for comp in comparison_data['components']:
                    if attr_name in comp['important_attributes']:
                        unit = comp['important_attributes'][attr_name]['unit']
                        attr_type = 'important'
                        break
                    elif attr_name in comp['additional_attributes']:
                        unit = comp['additional_attributes'][attr_name]['unit']
                        break
                comparison_data['all_attributes'].append({
                    'name': attr_name,
                    'unit': unit,
                    'type': attr_type
                })
        
        return JsonResponse(comparison_data)
        
    except Exception as e:
        return JsonResponse({'error': f'Error processing comparison: {str(e)}'}, status=500)