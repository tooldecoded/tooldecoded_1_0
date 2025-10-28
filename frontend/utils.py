from django.db.models import Q
from toolanalysis.models import ItemCategories


def get_category_hierarchy_filters(queryset, category_level1, category_level2, category_level3, model_type='products'):
    """
    Apply category hierarchy filtering to a queryset.
    
    Args:
        queryset: The queryset to filter
        category_level1: Level 1 category ID
        category_level2: Level 2 category ID  
        category_level3: Level 3 category ID
        model_type: 'products' or 'components' to determine the relationship field
    
    Returns:
        Filtered queryset
    """
    if model_type == 'products':
        category_field = 'itemcategories'
    elif model_type == 'components':
        category_field = 'itemcategories'
    else:
        raise ValueError("model_type must be 'products' or 'components'")
    
    # Category filtering with hierarchy support (includes child categories)
    if category_level3:
        # Level 3: only filter by this specific category
        return queryset.filter(**{f'{category_field}__id': category_level3})
    elif category_level2:
        # Level 2: include this category and all Level 3 children
        level3_ids = ItemCategories.objects.filter(parent=category_level2).values_list('id', flat=True)
        descendant_ids = [category_level2] + list(level3_ids)
        return queryset.filter(**{f'{category_field}__id__in': descendant_ids})
    elif category_level1:
        # Level 1: include this category and all Level 2/3 descendants
        level2_ids = ItemCategories.objects.filter(parent=category_level1).values_list('id', flat=True)
        level3_ids = ItemCategories.objects.filter(parent__in=level2_ids).values_list('id', flat=True)
        all_ids = [category_level1] + list(level2_ids) + list(level3_ids)
        return queryset.filter(**{f'{category_field}__id__in': all_ids})
    
    return queryset


def build_category_hierarchy_data(queryset, category_level1, category_level2, category_level3, model_type='products'):
    """
    Build category hierarchy data for cascading dropdowns.
    
    Args:
        queryset: The queryset to get categories from
        category_level1: Level 1 category ID
        category_level2: Level 2 category ID
        category_level3: Level 3 category ID
        model_type: 'products' or 'components' to determine the relationship field
    
    Returns:
        Dictionary with level1_categories, level2_categories, level3_categories, 
        level2_categories_with_parent, level3_categories_with_parent
    """
    if model_type == 'products':
        category_field = 'products'
    elif model_type == 'components':
        category_field = 'components'
    else:
        raise ValueError("model_type must be 'products' or 'components'")
    
    # Get all category IDs that have items matching the queryset
    relevant_category_ids = set()
    
    # Get Level 3 categories that have items
    level3_with_items = ItemCategories.objects.filter(
        level=3, 
        **{f'{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level3_with_items)
    
    # Get Level 2 categories that have items or have children with items
    level2_with_items = ItemCategories.objects.filter(
        level=2,
        **{f'{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_items)
    
    level2_with_children_items = ItemCategories.objects.filter(
        level=2,
        **{f'itemcategories__{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level2_with_children_items)
    
    # Get Level 1 categories that have items
    level1_with_items = ItemCategories.objects.filter(
        level=1,
        **{f'{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_items)
    
    level1_with_children_items = ItemCategories.objects.filter(
        level=1,
        **{f'itemcategories__{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_children_items)
    
    level1_with_grandchildren_items = ItemCategories.objects.filter(
        level=1,
        **{f'itemcategories__itemcategories__{category_field}__in': queryset}
    ).values_list('id', flat=True)
    relevant_category_ids.update(level1_with_grandchildren_items)
    
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
    
    return {
        'level1_categories': level1_categories,
        'level2_categories': level2_categories,
        'level3_categories': level3_categories,
        'level2_categories_with_parent': level2_categories_with_parent,
        'level3_categories_with_parent': level3_categories_with_parent,
    }
