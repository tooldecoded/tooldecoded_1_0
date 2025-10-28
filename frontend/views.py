from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, Value, F, FloatField
from django.db.models.functions import Cast
from toolanalysis.models import (
    Products, Components, Brands, BatteryVoltages, BatteryPlatforms, 
    ItemCategories, Statuses, ListingTypes, ComponentAttributes, Attributes,
    ProductLines, ProductComponents
)
from .models import LearningArticle, Tag, SiteSettings

def index(request):
    """Product catalog with filtering and pagination"""
    # Get filter parameters
    search = request.GET.get('search', '')
    brand = request.GET.get('brand', '')
    voltage = request.GET.get('voltage', '')
    platform = request.GET.get('platform', '')
    category_level1 = request.GET.get('category_level1', '')
    category_level2 = request.GET.get('category_level2', '')
    category_level3 = request.GET.get('category_level3', '')
    status = request.GET.get('status', '')
    listing_type = request.GET.get('listing_type', '')
    sort = request.GET.get('sort', 'name')
    sort_direction = request.GET.get('sort_direction', 'asc')
    page = int(request.GET.get('page', 1))
    
    # Parse multi-select values - handle both single values and comma-separated
    # First try to get from individual checkbox parameters (most common)
    brand_ids = request.GET.getlist('brand')
    voltage_ids = request.GET.getlist('voltage')
    platform_ids = request.GET.getlist('platform')
    status_ids = request.GET.getlist('status')
    listing_type_ids = request.GET.getlist('listing_type')
    
    # If no individual values, try comma-separated values
    if not brand_ids and brand:
        brand_ids = [x.strip() for x in brand.split(',')]
    if not voltage_ids and voltage:
        voltage_ids = [x.strip() for x in voltage.split(',')]
    if not platform_ids and platform:
        platform_ids = [x.strip() for x in platform.split(',')]
    if not status_ids and status:
        status_ids = [x.strip() for x in status.split(',')]
    if not listing_type_ids and listing_type:
        listing_type_ids = [x.strip() for x in listing_type.split(',')]
    
    
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
    
    # Category filtering with hierarchy support (includes child categories)
    if category_level3:
        # Level 3: only filter by this specific category
        products = products.filter(itemcategories__id=category_level3)
    elif category_level2:
        # Level 2: include this category and all Level 3 children
        level3_ids = ItemCategories.objects.filter(parent=category_level2).values_list('id', flat=True)
        descendant_ids = [category_level2] + list(level3_ids)
        products = products.filter(itemcategories__id__in=descendant_ids)
    elif category_level1:
        # Level 1: include this category and all Level 2/3 descendants
        level2_ids = ItemCategories.objects.filter(parent=category_level1).values_list('id', flat=True)
        level3_ids = ItemCategories.objects.filter(parent__in=level2_ids).values_list('id', flat=True)
        all_ids = [category_level1] + list(level2_ids) + list(level3_ids)
        products = products.filter(itemcategories__id__in=all_ids)
    
    if status_ids:
        products = products.filter(status__in=status_ids)
    
    if listing_type_ids:
        products = products.filter(listingtype__in=listing_type_ids)
    
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
    
    # Get filter options - filter by non-category filters to avoid circular dependency
    # Start with products filtered by everything EXCEPT categories
    non_category_products = Products.objects.select_related('brand', 'status', 'listingtype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemcategories'
    ).all()
    
    # Apply non-category filters
    if search:
        non_category_products = non_category_products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(sku__icontains=search)
        )
    
    if brand_ids:
        non_category_products = non_category_products.filter(brand__id__in=brand_ids)
    
    if voltage_ids:
        non_category_products = non_category_products.filter(batteryvoltages__id__in=voltage_ids)
    
    if platform_ids:
        non_category_products = non_category_products.filter(batteryplatforms__id__in=platform_ids)
    
    if status_ids:
        non_category_products = non_category_products.filter(status__in=status_ids)
    
    if listing_type_ids:
        non_category_products = non_category_products.filter(listingtype__in=listing_type_ids)
    
    # Get all available filter options - don't filter by current selections
    brands = Brands.objects.filter(products__isnull=False).distinct().order_by('name')
    voltages = BatteryVoltages.objects.filter(products__isnull=False).distinct().order_by('value')
    platforms = BatteryPlatforms.objects.filter(products__isnull=False).distinct().order_by('name')
    statuses = Statuses.objects.filter(products__isnull=False).distinct().order_by('sortorder')
    listing_types = ListingTypes.objects.filter(products__isnull=False).distinct().order_by('name')
    
    # Get categories - filter by non-category filtered products to show only relevant categories
    # First, get all category IDs that have products matching the non-category filters
    relevant_category_ids = set()
    
    # Get Level 3 categories that have products
    level3_with_products = ItemCategories.objects.filter(
        level=3, 
        products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level3_with_products)
    
    # Get Level 2 categories that have products or have children with products
    level2_with_products = ItemCategories.objects.filter(
        level=2,
        products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_products)
    
    # Get Level 2 categories that have children with products
    level2_with_children_products = ItemCategories.objects.filter(
        level=2,
        itemcategories__products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_children_products)
    
    # Get Level 1 categories that have products
    level1_with_products = ItemCategories.objects.filter(
        level=1,
        products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_products)
    
    # Get Level 1 categories that have children with products
    level1_with_children_products = ItemCategories.objects.filter(
        level=1,
        itemcategories__products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_children_products)
    
    # Get Level 1 categories that have grandchildren with products
    level1_with_grandchildren_products = ItemCategories.objects.filter(
        level=1,
        itemcategories__itemcategories__products__in=non_category_products
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_grandchildren_products)
    
    # Now filter categories based on the relevant IDs and parent selection
    if category_level1:
        level1_categories = ItemCategories.objects.filter(
            level=1, 
            id__in=relevant_category_ids
        ).order_by('sortorder', 'name')
        
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            parent=category_level1,
            id__in=relevant_category_ids
        ).order_by('parent__sortorder', 'sortorder', 'name')
        
        if category_level2:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent=category_level2,
                id__in=relevant_category_ids
            ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
        else:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent__parent=category_level1,
                id__in=relevant_category_ids
            ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
    else:
        level1_categories = ItemCategories.objects.filter(
            level=1, 
            id__in=relevant_category_ids
        ).order_by('sortorder', 'name')
        
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            id__in=relevant_category_ids
        ).order_by('parent__sortorder', 'sortorder', 'name')
        
        level3_categories = ItemCategories.objects.filter(
            level=3, 
            id__in=relevant_category_ids
        ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
    
    # Get categories with parent for cascading dropdowns
    level2_categories_with_parent = level2_categories.values('id', 'name', 'parent', 'sortorder')
    level3_categories_with_parent = level3_categories.values('id', 'name', 'parent', 'sortorder')
    
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
        },
        'listing_types': {
            'selected': len(listing_type_ids),
            'total': listing_types.count()
        }
    }
    
    context = {
        'products': page_obj,
        'brands': brands,
        'voltages': voltages,
        'platforms': platforms,
        'level1_categories': level1_categories,
        'level2_categories': level2_categories,
        'level3_categories': level3_categories,
        'level2_categories_with_parent': level2_categories_with_parent,
        'level3_categories_with_parent': level3_categories_with_parent,
        'statuses': statuses,
        'listing_types': listing_types,
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
            'listing_type': listing_type,
            'sort': sort,
            'sort_direction': sort_direction,
        },
        'selected_brand_ids': brand_ids,
        'selected_voltage_ids': voltage_ids,
        'selected_platform_ids': platform_ids,
        'selected_status_ids': status_ids,
        'selected_listing_type_ids': listing_type_ids,
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
    if category_level3:
        components = components.filter(itemcategories__id=category_level3)
    elif category_level2:
        level3_ids = ItemCategories.objects.filter(parent=category_level2).values_list('id', flat=True)
        descendant_ids = [category_level2] + list(level3_ids)
        components = components.filter(itemcategories__id__in=descendant_ids)
    elif category_level1:
        level2_ids = ItemCategories.objects.filter(parent=category_level1).values_list('id', flat=True)
        level3_ids = ItemCategories.objects.filter(parent__in=level2_ids).values_list('id', flat=True)
        all_ids = [category_level1] + list(level2_ids) + list(level3_ids)
        components = components.filter(itemcategories__id__in=all_ids)
    
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
    
    # Get categories - filter by non-category filtered components
    relevant_category_ids = set()
    
    # Get Level 3 categories that have components
    level3_with_components = ItemCategories.objects.filter(
        level=3, 
        components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level3_with_components)
    
    # Get Level 2 categories that have components or have children with components
    level2_with_components = ItemCategories.objects.filter(
        level=2,
        components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_components)
    
    level2_with_children_components = ItemCategories.objects.filter(
        level=2,
        itemcategories__components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_children_components)
    
    # Get Level 1 categories that have components
    level1_with_components = ItemCategories.objects.filter(
        level=1,
        components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_components)
    
    level1_with_children_components = ItemCategories.objects.filter(
        level=1,
        itemcategories__components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_children_components)
    
    level1_with_grandchildren_components = ItemCategories.objects.filter(
        level=1,
        itemcategories__itemcategories__components__in=non_category_components
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_grandchildren_components)
    
    # Filter categories based on relevant IDs and parent selection
    if category_level1:
        level1_categories = ItemCategories.objects.filter(
            level=1, 
            id__in=relevant_category_ids
        ).order_by('sortorder', 'name')
        
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            parent=category_level1,
            id__in=relevant_category_ids
        ).order_by('parent__sortorder', 'sortorder', 'name')
        
        if category_level2:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent=category_level2,
                id__in=relevant_category_ids
            ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
        else:
            level3_categories = ItemCategories.objects.filter(
                level=3, 
                parent__parent=category_level1,
                id__in=relevant_category_ids
            ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
    else:
        level1_categories = ItemCategories.objects.filter(
            level=1, 
            id__in=relevant_category_ids
        ).order_by('sortorder', 'name')
        
        level2_categories = ItemCategories.objects.filter(
            level=2, 
            id__in=relevant_category_ids
        ).order_by('parent__sortorder', 'sortorder', 'name')
        
        level3_categories = ItemCategories.objects.filter(
            level=3, 
            id__in=relevant_category_ids
        ).order_by('parent__parent__sortorder', 'parent__sortorder', 'sortorder', 'name')
    
    # Get categories with parent for cascading dropdowns
    level2_categories_with_parent = level2_categories.values('id', 'name', 'parent', 'sortorder')
    level3_categories_with_parent = level3_categories.values('id', 'name', 'parent', 'sortorder')
    
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

def home(request):
    """Home page with site overview and statistics"""
    # Get basic statistics for the home page
    total_products = Products.objects.count()
    total_components = Components.objects.count()
    total_brands = Brands.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    total_categories = ItemCategories.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    
    # Get some popular categories for the home page
    try:
        # Power Tools (Level 1)
        power_tools_category = ItemCategories.objects.filter(
            name='Power Tools', level=1
        ).first()
        power_tools_category_id = str(power_tools_category.id) if power_tools_category else ''
        
        # Batteries and Chargers (Level 2)
        batteries_chargers_category = ItemCategories.objects.filter(
            name='Batteries and Chargers', level=2
        ).first()
        batteries_chargers_category_id = str(batteries_chargers_category.id) if batteries_chargers_category else ''
        
        # Outdoor Power Equipment (Level 1)
        outdoor_category = ItemCategories.objects.filter(
            name='Outdoor Power Equipment', level=1
        ).first()
        outdoor_category_id = str(outdoor_category.id) if outdoor_category else ''
        
        # Shop, Cleaning and Lifestyle (Level 1)
        shop_cleaning_category = ItemCategories.objects.filter(
            name='Shop, Cleaning and Lifestyle', level=1
        ).first()
        shop_cleaning_category_id = str(shop_cleaning_category.id) if shop_cleaning_category else ''
    except:
        power_tools_category_id = ''
        batteries_chargers_category_id = ''
        outdoor_category_id = ''
        shop_cleaning_category_id = ''
    
    context = {
        'total_products': total_products,
        'total_components': total_components,
        'total_brands': total_brands,
        'total_categories': total_categories,
        'power_tools_category_id': power_tools_category_id,
        'batteries_chargers_category_id': batteries_chargers_category_id,
        'outdoor_category_id': outdoor_category_id,
        'shop_cleaning_category_id': shop_cleaning_category_id,
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