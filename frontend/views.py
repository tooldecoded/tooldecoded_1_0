from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, Value, F, FloatField
from django.db.models.functions import Cast
from django.http import JsonResponse
import uuid
from toolanalysis.models import (
    Products, Components, Brands, BatteryVoltages, BatteryPlatforms, 
    Categories, Subcategories, ItemTypes, Statuses, ListingTypes, ComponentAttributes, Attributes,
    ProductLines, ProductComponents, Features, ComponentFeatures
)
from .models import LearningArticle, Tag, SiteSettings
from .utils import get_category_hierarchy_filters
from . import catalog_utils

# ============================================================================
# CATALOG VIEWS - UNIFIED IMPLEMENTATION
# ============================================================================

def index(request):
    """Unified product catalog view using shared utilities."""
    # Parse filter parameters
    filters = catalog_utils.parse_filter_params(request)
    
    # Build filtered queryset
    products = catalog_utils.build_filter_query(Products, filters)
    
    # Apply sorting
    products = catalog_utils.apply_sorting(products, filters['sort'], filters['sort_direction'], Products)
    
    # Paginate results
    page_obj = catalog_utils.paginate_results(products, filters['page'], filters['page_size'])
    
    # Get filter options
    filter_options = catalog_utils.get_filter_options(filters, Products)
    
    # Calculate filter counts
    filter_counts = catalog_utils.calculate_filter_counts(filters, filter_options)
    
    context = {
        'products': page_obj,
        'brands': filter_options['brands'],
        'voltages': filter_options['voltages'],
        'platforms': filter_options['platforms'],
        'statuses': filter_options['statuses'],
        'categories': filter_options['categories'],
        'subcategories': filter_options['subcategories'],
        'itemtypes': filter_options['itemtypes'],
        'filter_counts': filter_counts,
        'current_filters': {
            'search': filters['search'],
            'brand': request.GET.get('brand', ''),
            'voltage': request.GET.get('voltage', ''),
            'platform': request.GET.get('platform', ''),
            'category': request.GET.get('category', ''),
            'subcategory': request.GET.get('subcategory', ''),
            'itemtype': request.GET.get('itemtype', ''),
            'status': request.GET.get('status', ''),
            'release_date_from': filters['release_date_from'],
            'release_date_to': filters['release_date_to'],
            'sort': filters['sort'],
            'sort_direction': filters['sort_direction'],
        },
        'selected_brand_ids': filters['brand_ids'],
        'selected_voltage_ids': filters['voltage_ids'],
        'selected_platform_ids': filters['platform_ids'],
        'selected_status_ids': filters['status_ids'],
        'selected_category_ids': filters['category_ids'],
        'selected_subcategory_ids': filters['subcategory_ids'],
        'selected_itemtype_ids': filters['itemtype_ids'],
        'item_type': 'product',  # For template differentiation
    }
    
    return render(request, 'frontend/products.html', context)


def components_index(request):
    """Unified component catalog view using shared utilities."""
    # Parse filter parameters
    filters = catalog_utils.parse_filter_params(request)
    
    # Build filtered queryset
    components = catalog_utils.build_filter_query(Components, filters)
    
    # Apply sorting
    components = catalog_utils.apply_sorting(components, filters['sort'], filters['sort_direction'], Components)
    
    # Paginate results (components use 12 per page by default)
    if not request.GET.get('page_size'):
        filters['page_size'] = 12
    page_obj = catalog_utils.paginate_results(components, filters['page'], filters['page_size'])
    
    # Get filter options
    filter_options = catalog_utils.get_filter_options(filters, Components)
    
    # Calculate filter counts
    filter_counts = catalog_utils.calculate_filter_counts(filters, filter_options)
    
    # Get features for filtering (using new Features system)
    # Features are now included in filter_options from catalog_utils
    
    # Get attributes with their values for filtering (specifications only)
    non_category_components = catalog_utils.build_filter_query(Components, filters)
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
    
    # Sort values for each attribute
    regular_attributes = []
    for attr_data in attributes_dict.values():
        attr_data['values'].sort()
        regular_attributes.append(attr_data)
    
    # Get site settings for fair price feature
    site_settings = SiteSettings.get_settings()
    
    context = {
        'components': page_obj,
        'brands': filter_options['brands'],
        'voltages': filter_options['voltages'],
        'platforms': filter_options['platforms'],
        'product_lines': filter_options['product_lines'],
        'categories': filter_options['categories'],
        'subcategories': filter_options['subcategories'],
        'itemtypes': filter_options['itemtypes'],
        'motor_types': filter_options.get('motor_types', []),
        'features': filter_options.get('features', []),
        'attributes': regular_attributes,
        'filter_counts': filter_counts,
        'current_filters': {
            'search': filters['search'],
            'brand': request.GET.get('brand', ''),
            'voltage': request.GET.get('voltage', ''),
            'platform': request.GET.get('platform', ''),
            'category': request.GET.get('category', ''),
            'subcategory': request.GET.get('subcategory', ''),
            'itemtype': request.GET.get('itemtype', ''),
            'product_line': request.GET.get('product_line', ''),
            'listing_type': request.GET.get('listing_type', ''),
            'motor_type': request.GET.get('motor_type', ''),
            'sort': filters['sort'],
            'sort_direction': filters['sort_direction'],
        },
        'selected_brand_ids': filters['brand_ids'],
        'selected_voltage_ids': filters['voltage_ids'],
        'selected_platform_ids': filters['platform_ids'],
        'selected_product_line_ids': filters['product_line_ids'],
        'selected_category_ids': filters['category_ids'],
        'selected_subcategory_ids': filters['subcategory_ids'],
        'selected_itemtype_ids': filters['itemtype_ids'],
        'selected_motor_type_ids': filters['motor_type_ids'],
        'selected_attribute_filters': filters['attribute_filters'],
        'selected_feature_filters': filters['feature_filters'],
        'selected_feature_ids': filters['feature_ids'],
        'show_fair_price': site_settings.show_fair_price_feature,
        'item_type': 'component',  # For template differentiation
    }
    
    return render(request, 'frontend/components.html', context)



def product_detail(request, product_id):
    """Product detail view"""
    product = get_object_or_404(Products, id=product_id)
    
    # Get product components with proper prefetching
    product_components = ProductComponents.objects.filter(
        product=product
    ).select_related('component__brand').prefetch_related(
        'component__componentattributes_set__attribute',
        'component__itemtypes'
    ).all()
    
    # Group components by their item types for the comparison table
    component_groups = {}
    for pc in product_components:
        component = pc.component
        # Get the primary item type for grouping
        primary_itemtype = component.itemtypes.first()
        if primary_itemtype:
            itemtype_name = primary_itemtype.name
            if itemtype_name not in component_groups:
                # Get all attributes for this item type to create columns
                itemtype_attributes = Attributes.objects.filter(
                    itemtypes=primary_itemtype
                ).order_by('name')
                
                component_groups[itemtype_name] = {
                    'itemtype': primary_itemtype,
                    'components': [],
                    'columns': list(itemtype_attributes)
                }
            
            # Add component data - simplified structure
            component_groups[itemtype_name]['components'].append(pc)
    
    # Get component product images (if any) - placeholder for now
    component_products = {}
    
    current_filters = {
        'sort': 'name',
        'sort_direction': 'asc'
    }
    
    context = {
        'product': product,
        'component_groups': component_groups,
        'component_products': component_products,
        'current_filters': current_filters,
    }
    
    return render(request, 'frontend/product_detail.html', context)


def component_detail(request, component_id):
    """Component detail view"""
    component = get_object_or_404(Components, id=component_id)
    
    # Get all component attributes
    component_attributes = ComponentAttributes.objects.filter(component=component).select_related('attribute')
    
    # Get category-designated attributes from component's ItemTypes
    category_attributes = Attributes.objects.filter(
        itemtypes__in=component.itemtypes.all()
    ).distinct()
    
    # Separate important vs additional attributes
    # Important attributes are those that are designated for the component's categories
    important_attributes = component_attributes.filter(attribute__in=category_attributes)
    # Additional attributes are everything else
    additional_attributes = component_attributes.exclude(attribute__in=category_attributes)
    
    # Get component features
    component_features = ComponentFeatures.objects.filter(component=component).select_related('feature')
    
    # Get products that use this component
    product_components = ProductComponents.objects.filter(component=component).select_related('product').prefetch_related('product__productimages_set')
    
    # Get site settings for fair price feature
    site_settings = SiteSettings.get_settings()
    
    context = {
        'component': component,
        'important_attributes': important_attributes,
        'additional_attributes': additional_attributes,
        'component_features': component_features,
        'product_components': product_components,
        'show_fair_price': site_settings.show_fair_price_feature,
    }
    
    return render(request, 'frontend/component_detail.html', context)

def browse_flagship(request):
    """Browse flagship components organized by item type - curated showcase view"""
    # Query featured components ordered by showcase priority, then name
    flagship_components = Components.objects.filter(
        is_featured=True
    ).select_related('brand').prefetch_related(
        'batteryvoltages', 'batteryplatforms', 'itemtypes', 'componentattributes_set__attribute'
    ).order_by('-showcase_priority', 'name')
    
    # Organize components by primary item type
    organized_products = {}
    itemtype_metadata = []  # For sidebar navigation
    
    for component in flagship_components:
        # Get the primary item type for this component
        primary_itemtype = component.itemtypes.first()
        
        if primary_itemtype:
            itemtype_name = primary_itemtype.name
            itemtype_slug = itemtype_name.lower().replace(' ', '-').replace('&', 'and')
            
            if itemtype_name not in organized_products:
                organized_products[itemtype_name] = {
                    'itemtype': primary_itemtype,
                    'itemtype_slug': itemtype_slug,
                    'components': []
                }
            
            organized_products[itemtype_name]['components'].append(component)
    
    # Create item type metadata for sidebar navigation
    for itemtype_name, itemtype_data in organized_products.items():
        itemtype_metadata.append({
            'name': itemtype_name,
            'slug': itemtype_data['itemtype_slug'],
            'count': len(itemtype_data['components']),
            'sortorder': itemtype_data['itemtype'].sortorder or 0
        })
    
    # Sort item types by sortorder, then by name
    itemtype_metadata.sort(key=lambda x: (x['sortorder'], x['name']))
    
    context = {
        'organized_products': organized_products,
        'itemtype_metadata': itemtype_metadata,
        'has_products': flagship_components.exists(),
    }
    
    return render(request, 'frontend/browse.html', context)

def home(request):
    """Home page with site overview and statistics"""
    # Get basic statistics for the home page
    total_products = Products.objects.count()
    total_components = Components.objects.count()
    total_brands = Brands.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    total_categories = Categories.objects.filter(Q(products__isnull=False) | Q(components__isnull=False)).distinct().count()
    
    # Get latest published articles (first 4)
    latest_articles = LearningArticle.objects.filter(
        is_published=True
    ).prefetch_related('tags')[:4]
    
    # Get flagship components preview (first 4 featured components)
    flagship_preview = Components.objects.filter(
        is_featured=True
    ).select_related('brand').prefetch_related('categories', 'subcategories', 'itemtypes')[:4]
    
    # Get recent products (latest 3 by release date)
    recent_products = Products.objects.select_related('brand').prefetch_related('productimages_set').order_by('-releasedate')[:3]
    
    # Get recent components (latest 3)
    recent_components = Components.objects.select_related('brand').order_by('-id')[:3]
    
    context = {
        'total_products': total_products,
        'total_components': total_components,
        'total_brands': total_brands,
        'total_categories': total_categories,
        'latest_articles': latest_articles,
        'flagship_preview': flagship_preview,
        'recent_products': recent_products,
        'recent_components': recent_components,
        'has_flagship_products': Components.objects.filter(is_featured=True).exists(),
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
    category = request.GET.get('category', '')
    subcategory = request.GET.get('subcategory', '')
    itemtype = request.GET.get('itemtype', '')
    
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
        'batteryvoltages', 'batteryplatforms', 'categories', 'subcategories', 'itemtypes'
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
    if category:
        subcategories = Subcategories.objects.filter(
            categories__id=category,
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        
        if subcategory:
            itemtypes = ItemTypes.objects.filter(
                subcategories__id=subcategory,
                products__in=products
            ).distinct().order_by('sortorder', 'name')
        else:
            itemtypes = ItemTypes.objects.filter(
                categories__id=category,
                products__in=products
            ).distinct().order_by('sortorder', 'name')
    else:
        categories = Categories.objects.filter(
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        subcategories = Subcategories.objects.filter(
            products__in=products
        ).distinct().order_by('sortorder', 'name')
        itemtypes = ItemTypes.objects.filter(
            products__in=products
        ).distinct().order_by('sortorder', 'name')
    
    return JsonResponse({
        'brands': [{'id': b.id, 'name': b.name} for b in brands],
        'voltages': [{'id': v.id, 'value': v.value} for v in voltages],
        'platforms': [{'id': p.id, 'name': p.name} for p in platforms],
        'categories': [{'id': c.id, 'name': c.name} for c in categories] if 'categories' in locals() else [],
        'subcategories': [{'id': c.id, 'name': c.name} for c in subcategories],
        'itemtypes': [{'id': c.id, 'name': c.name} for c in itemtypes],
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
            component = Components.objects.select_related('brand', 'motortype').prefetch_related(
                'itemtypes__attributes', 'componentattributes_set__attribute', 'componentfeatures_set__feature'
            ).get(id=item_id)
            
            # Get category-designated attributes (key attributes)
            category_attributes = Attributes.objects.filter(
                itemtypes__in=component.itemtypes.all()
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
            
            # Get component features
            component_features = ComponentFeatures.objects.filter(component=component).select_related('feature')
            features = []
            for comp_feature in component_features:
                features.append({
                    'name': comp_feature.feature.name,
                    'value': comp_feature.value or 'Yes'
                })
            
            return JsonResponse({
                'name': component.name,
                'brand': component.brand.name if component.brand else '',
                'sku': component.sku or '',
                'image': component.image or '',
                'description': component.description or '',
                'motor_type': component.motortype.name if component.motortype else None,
                'key_attributes': key_attributes,
                'features': features,
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
            'batteryvoltages', 'batteryplatforms', 'categories', 'subcategories', 'itemtypes', 'productlines',
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
                itemtypes__in=component.itemtypes.all()
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
                'categories': [c.name for c in component.categories.all()],
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

# ============================================================================
# END DEPRECATED SECTION
# ============================================================================