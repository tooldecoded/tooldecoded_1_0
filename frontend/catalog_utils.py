"""
Shared utility functions for product and component catalog views.
This module provides generic filtering, sorting, and pagination logic
that works with both Products and Components models.
"""

from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, F, FloatField
from django.db.models.functions import Cast
import uuid
from toolanalysis.models import (
    Products, Components, Brands, BatteryVoltages, BatteryPlatforms,
    Categories, Subcategories, ItemTypes, Statuses, ProductLines, Features, MotorTypes
)


def parse_filter_params(request):
    """
    Parse and structure filter parameters from request.
    Returns a dictionary with parsed filter values.
    """
    # Get basic filter parameters
    filters = {
        'search': request.GET.get('search', ''),
        'sort': request.GET.get('sort', 'name'),
        'sort_direction': request.GET.get('sort_direction', 'asc'),
        'page': int(request.GET.get('page', 1)),
        'page_size': int(request.GET.get('page_size', 12)),
        'release_date_from': request.GET.get('release_date_from', ''),
        'release_date_to': request.GET.get('release_date_to', ''),
    }
    
    # Parse multi-select values for categories
    filters['category_ids'] = request.GET.getlist('category[]')
    filters['subcategory_ids'] = request.GET.getlist('subcategory[]')
    filters['itemtype_ids'] = request.GET.getlist('itemtype[]')
    
    # Parse multi-select values for other filters
    filters['brand_ids'] = request.GET.getlist('brand')
    filters['voltage_ids'] = request.GET.getlist('voltage')
    filters['platform_ids'] = request.GET.getlist('platform')
    filters['status_ids'] = request.GET.getlist('status')
    filters['product_line_ids'] = request.GET.getlist('product_line')
    filters['listing_type_ids'] = request.GET.getlist('listing_type')
    filters['motor_type_ids'] = request.GET.getlist('motor_type')
    
    # Handle comma-separated values if no individual values
    if not filters['brand_ids'] and request.GET.get('brand'):
        filters['brand_ids'] = [x.strip() for x in request.GET.get('brand').split(',')]
    if not filters['voltage_ids'] and request.GET.get('voltage'):
        filters['voltage_ids'] = [x.strip() for x in request.GET.get('voltage').split(',')]
    if not filters['platform_ids'] and request.GET.get('platform'):
        filters['platform_ids'] = [x.strip() for x in request.GET.get('platform').split(',')]
    if not filters['status_ids'] and request.GET.get('status'):
        filters['status_ids'] = [x.strip() for x in request.GET.get('status').split(',')]
    if not filters['product_line_ids'] and request.GET.get('product_line'):
        filters['product_line_ids'] = [x.strip() for x in request.GET.get('product_line').split(',')]
    if not filters['listing_type_ids'] and request.GET.get('listing_type'):
        filters['listing_type_ids'] = [x.strip() for x in request.GET.get('listing_type').split(',')]
    if not filters['motor_type_ids'] and request.GET.get('motor_type'):
        filters['motor_type_ids'] = [x.strip() for x in request.GET.get('motor_type').split(',')]
    
    # Convert string IDs to UUIDs
    filters['brand_ids'] = _convert_to_uuids(filters['brand_ids'])
    filters['voltage_ids'] = _convert_to_uuids(filters['voltage_ids'])
    filters['platform_ids'] = _convert_to_uuids(filters['platform_ids'])
    filters['status_ids'] = _convert_to_uuids(filters['status_ids'])
    filters['product_line_ids'] = _convert_to_uuids(filters['product_line_ids'])
    filters['listing_type_ids'] = _convert_to_uuids(filters['listing_type_ids'])
    filters['motor_type_ids'] = _convert_to_uuids(filters['motor_type_ids'])
    
    # Parse attribute filters (for components)
    filters['attribute_filters'] = {}
    filters['feature_filters'] = {}
    filters['feature_ids'] = []
    for key, value in request.GET.items():
        if key.startswith('attr_'):
            attr_id = key.replace('attr_', '')
            attr_values = request.GET.getlist(key)
            if attr_values:
                filters['attribute_filters'][attr_id] = attr_values
        elif key.startswith('feature_'):
            feature_id = key.replace('feature_', '')
            feature_values = request.GET.getlist(key)
            if feature_values:
                filters['feature_filters'][feature_id] = feature_values
        elif key == 'features':
            # Handle new Features system
            feature_ids = request.GET.getlist('features')
            filters['feature_ids'] = _convert_to_uuids(feature_ids)
    
    return filters


def _convert_to_uuids(id_list):
    """Convert list of string IDs to UUID objects."""
    if not id_list:
        return []
    try:
        return [uuid.UUID(id_str) for id_str in id_list if id_str]
    except (ValueError, AttributeError):
        return []


def build_filter_query(model_class, filters):
    """
    Build filtered queryset based on filter parameters.
    Works with both Products and Components models.
    """
    # Start with all items
    queryset = model_class.objects.select_related('brand', 'listingtype', 'motortype').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemtypes'
    )
    
    # Add product-specific prefetch
    if model_class == Products:
        queryset = queryset.select_related('status')
    
    # Add component-specific prefetch
    if model_class == Components:
        queryset = queryset.prefetch_related('productlines')
    
    queryset = queryset.all()
    
    # Apply search filter
    if filters.get('search'):
        queryset = queryset.filter(
            Q(name__icontains=filters['search']) | 
            Q(description__icontains=filters['search']) |
            Q(sku__icontains=filters['search'])
        )
    
    # Apply brand filter
    if filters.get('brand_ids'):
        queryset = queryset.filter(brand__id__in=filters['brand_ids'])
    
    # Apply voltage filter
    if filters.get('voltage_ids'):
        queryset = queryset.filter(batteryvoltages__id__in=filters['voltage_ids'])
    
    # Apply platform filter
    if filters.get('platform_ids'):
        queryset = queryset.filter(batteryplatforms__id__in=filters['platform_ids'])
    
    # Apply category filters
    if filters.get('category_ids'):
        queryset = queryset.filter(categories__id__in=filters['category_ids'])
    if filters.get('subcategory_ids'):
        queryset = queryset.filter(subcategories__id__in=filters['subcategory_ids'])
    if filters.get('itemtype_ids'):
        queryset = queryset.filter(itemtypes__id__in=filters['itemtype_ids'])
    
    # Apply status filter (Products only)
    if model_class == Products and filters.get('status_ids'):
        queryset = queryset.filter(status__id__in=filters['status_ids'])
    
    # Apply product line filter (Components only)
    if model_class == Components and filters.get('product_line_ids'):
        queryset = queryset.filter(productlines__id__in=filters['product_line_ids'])
    
    # Apply listing type filter
    if filters.get('listing_type_ids'):
        queryset = queryset.filter(listingtype__in=filters['listing_type_ids'])
    
    # Apply motor type filter
    if filters.get('motor_type_ids'):
        queryset = queryset.filter(motortype__id__in=filters['motor_type_ids'])
    
    # Apply date range filters (Products only)
    if model_class == Products:
        if filters.get('release_date_from'):
            queryset = queryset.filter(releasedate__gte=filters['release_date_from'])
        if filters.get('release_date_to'):
            queryset = queryset.filter(releasedate__lte=filters['release_date_to'])
    
    # Apply attribute filters (Components only)
    if model_class == Components:
        if filters.get('attribute_filters'):
            for attr_id, attr_values in filters['attribute_filters'].items():
                queryset = queryset.filter(
                    componentattributes__attribute_id=attr_id,
                    componentattributes__value__in=attr_values
                ).distinct()
        
        if filters.get('feature_filters'):
            for feature_id, feature_values in filters['feature_filters'].items():
                lowercase_values = [val.lower() for val in feature_values]
                queryset = queryset.filter(
                    componentattributes__attribute_id=feature_id,
                    componentattributes__value__in=lowercase_values
                ).distinct()
        
        # Apply Features filtering (new system)
        if filters.get('feature_ids'):
            queryset = queryset.filter(features__id__in=filters['feature_ids']).distinct()
    
    return queryset


def apply_sorting(queryset, sort, sort_direction, model_class):
    """Apply sorting to queryset based on sort parameters."""
    if sort == 'brand':
        if sort_direction == 'desc':
            queryset = queryset.order_by('-brand__name', 'name')
        else:
            queryset = queryset.order_by('brand__name', 'name')
    elif sort == 'release_date' and model_class == Products:
        if sort_direction == 'desc':
            queryset = queryset.order_by('-releasedate', 'name')
        else:
            queryset = queryset.order_by('releasedate', 'name')
    elif sort == 'fair_price' and model_class == Components:
        # Extract fair_price from JSONField and handle nulls
        queryset = queryset.annotate(
            fair_price_value=Case(
                When(fair_price_narrative__fair_price__isnull=False,
                     then=Cast(F('fair_price_narrative__fair_price'), FloatField())),
                default=Value(None),
                output_field=FloatField()
            )
        )
        if sort_direction == 'desc':
            queryset = queryset.order_by(F('fair_price_value').desc(nulls_last=True), 'name')
        else:
            queryset = queryset.order_by(F('fair_price_value').asc(nulls_last=True), 'name')
    else:
        # Default: use category sortorder
        if sort_direction == 'desc':
            queryset = queryset.order_by('-categories__sortorder', '-subcategories__sortorder', '-itemtypes__sortorder', '-name').distinct()
        else:
            queryset = queryset.order_by('categories__sortorder', 'subcategories__sortorder', 'itemtypes__sortorder', 'name').distinct()
    
    return queryset


def paginate_results(queryset, page, page_size):
    """Paginate queryset and return page object."""
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    return page_obj


def get_filter_options(filters, model_class):
    """
    Get available filter options based on current filters.
    Returns dynamic filter options that update based on selections.
    """
    filter_options = {}
    
    # Build base querysets for each filter type (excluding that filter itself)
    # This allows filters to update dynamically based on other selections
    
    # Get the correct field name for the model
    model_field_name = 'products' if model_class == Products else 'components'
    
    # Brand filter options
    brand_base = _build_base_queryset(model_class, filters, exclude=['brand_ids'])
    filter_options['brands'] = Brands.objects.filter(
        **{f'{model_field_name}__in': brand_base}
    ).distinct().order_by('name')
    
    # Voltage filter options
    voltage_base = _build_base_queryset(model_class, filters, exclude=['voltage_ids'])
    filter_options['voltages'] = BatteryVoltages.objects.filter(
        **{f'{model_field_name}__in': voltage_base}
    ).distinct().order_by('value')
    
    # Platform filter options
    platform_base = _build_base_queryset(model_class, filters, exclude=['platform_ids'])
    filter_options['platforms'] = BatteryPlatforms.objects.filter(
        **{f'{model_field_name}__in': platform_base}
    ).distinct().order_by('name')
    
    # Category filter options (exclude category filters)
    category_base = _build_base_queryset(model_class, filters, exclude=['category_ids'])
    filter_options['categories'] = Categories.objects.filter(
        **{f'{model_field_name}__in': category_base}
    ).distinct().order_by('sortorder', 'name')
    
    # Subcategory filter options (exclude subcategory filters)
    subcategory_base = _build_base_queryset(model_class, filters, exclude=['subcategory_ids'])
    filter_options['subcategories'] = Subcategories.objects.filter(
        **{f'{model_field_name}__in': subcategory_base}
    ).distinct().order_by('sortorder', 'name')
    
    # Item type filter options (exclude itemtype filters)
    itemtype_base = _build_base_queryset(model_class, filters, exclude=['itemtype_ids'])
    filter_options['itemtypes'] = ItemTypes.objects.filter(
        **{f'{model_field_name}__in': itemtype_base}
    ).distinct().order_by('sortorder', 'name')
    
    # Motor type filter options (exclude motor_type filters)
    motor_type_base = _build_base_queryset(model_class, filters, exclude=['motor_type_ids'])
    filter_options['motor_types'] = MotorTypes.objects.filter(
        **{f'{model_field_name}__in': motor_type_base}
    ).distinct().order_by('sortorder', 'name')
    
    # Status filter options (Products only)
    if model_class == Products:
        status_base = _build_base_queryset(model_class, filters, exclude=['status_ids'])
        filter_options['statuses'] = Statuses.objects.filter(
            products__in=status_base
        ).distinct().order_by('name')
    
    # Product line filter options (Components only)
    if model_class == Components:
        product_line_base = _build_base_queryset(model_class, filters, exclude=['product_line_ids'])
        filter_options['product_lines'] = ProductLines.objects.filter(
            components__in=product_line_base
        ).distinct().order_by('name')
        
        # Features filter options (Components only)
        features_base = _build_base_queryset(model_class, filters, exclude=['feature_ids'])
        filter_options['features'] = Features.objects.filter(
            componentfeatures__component__in=features_base
        ).distinct().order_by('sortorder', 'name')
    
    return filter_options


def _build_base_queryset(model_class, filters, exclude=None):
    """
    Build a base queryset for filter options, excluding specified filters.
    This allows dynamic filter updates.
    """
    if exclude is None:
        exclude = []
    
    # Create a copy of filters without excluded keys
    temp_filters = {k: v for k, v in filters.items() if k not in exclude}
    
    return build_filter_query(model_class, temp_filters)


def calculate_filter_counts(filters, filter_options):
    """Calculate counts for active filters vs total available."""
    counts = {}
    
    counts['brands'] = {
        'selected': len(filters.get('brand_ids', [])),
        'total': filter_options['brands'].count()
    }
    
    counts['voltages'] = {
        'selected': len(filters.get('voltage_ids', [])),
        'total': filter_options['voltages'].count()
    }
    
    counts['platforms'] = {
        'selected': len(filters.get('platform_ids', [])),
        'total': filter_options['platforms'].count()
    }
    
    if 'statuses' in filter_options:
        counts['statuses'] = {
            'selected': len(filters.get('status_ids', [])),
            'total': filter_options['statuses'].count()
        }
    
    if 'product_lines' in filter_options:
        counts['product_lines'] = {
            'selected': len(filters.get('product_line_ids', [])),
            'total': filter_options['product_lines'].count()
        }
    
    if 'features' in filter_options:
        counts['features'] = {
            'selected': len(filters.get('feature_ids', [])),
            'total': filter_options['features'].count()
        }
    
    if 'motor_types' in filter_options:
        counts['motor_types'] = {
            'selected': len(filters.get('motor_type_ids', [])),
            'total': filter_options['motor_types'].count()
        }
    
    return counts


