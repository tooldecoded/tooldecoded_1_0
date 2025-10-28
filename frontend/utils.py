from django.db.models import Q
from toolanalysis.models import ItemCategories, Categories, Subcategories, ItemTypes


def get_category_hierarchy_filters(queryset, category, subcategory, itemtype, model_type='products'):
    """
    Apply category hierarchy filtering to a queryset using the new three-table structure.
    
    Args:
        queryset: The queryset to filter
        category: Category ID
        subcategory: Subcategory ID  
        itemtype: ItemType ID
        model_type: 'products' or 'components' to determine the relationship field
    
    Returns:
        Filtered queryset
    """
    if model_type == 'products':
        category_field = 'categories'
        subcategory_field = 'subcategories'
        itemtype_field = 'itemtypes'
    elif model_type == 'components':
        category_field = 'categories'
        subcategory_field = 'subcategories'
        itemtype_field = 'itemtypes'
    else:
        raise ValueError("model_type must be 'products' or 'components'")
    
    # Category filtering with hierarchy support
    if itemtype:
        # ItemType: only filter by this specific item type
        return queryset.filter(**{f'{itemtype_field}__id': itemtype})
    elif subcategory:
        # Subcategory: include this subcategory and all its item types
        itemtype_ids = ItemTypes.objects.filter(subcategories__id=subcategory).values_list('id', flat=True)
        descendant_ids = [subcategory] + list(itemtype_ids)
        return queryset.filter(**{f'{subcategory_field}__id__in': descendant_ids})
    elif category:
        # Category: include this category and all its subcategories and item types
        subcategory_ids = Subcategories.objects.filter(categories__id=category).values_list('id', flat=True)
        itemtype_ids = ItemTypes.objects.filter(categories__id=category).values_list('id', flat=True)
        all_ids = [category] + list(subcategory_ids) + list(itemtype_ids)
        return queryset.filter(**{f'{category_field}__id__in': all_ids})
    
    return queryset
