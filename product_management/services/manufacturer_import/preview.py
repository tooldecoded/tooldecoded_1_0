"""Preview and diff builder for import review."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from toolanalysis.models import Components, Products

from .base import ParsedProductData
from .mapper import ManufacturerDataMapper


@dataclass
class FieldDiff:
    """Represents a field difference between existing and new data."""
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed: bool = False


@dataclass
class ImportPreview:
    """Preview of what will be created/updated during import."""
    status: str  # "new", "update", "conflict"
    existing_product: Optional[Products] = None
    existing_component: Optional[Components] = None
    parsed_data: Optional[ParsedProductData] = None
    field_diffs: List[FieldDiff] = field(default_factory=list)
    missing_critical: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    will_create: Dict[str, int] = field(default_factory=dict)
    
    # Component/Product data for preview
    product_data: Dict = field(default_factory=dict)
    component_data: Dict = field(default_factory=dict)
    included_components: List[Dict] = field(default_factory=list)
    product_specifications: List[Dict] = field(default_factory=list)  # For ProductSpecifications table
    component_attributes: List[Dict] = field(default_factory=list)  # For ComponentAttributes table
    component_features: List[Dict] = field(default_factory=list)  # For ComponentFeatures table
    categories: List[Dict] = field(default_factory=list)  # Mapped categories
    subcategories: List[Dict] = field(default_factory=list)  # Mapped subcategories
    itemtypes: List[Dict] = field(default_factory=list)  # Mapped itemtypes
    # Legacy fields for backwards compatibility
    attributes: List[Dict] = field(default_factory=list)
    features: List[Dict] = field(default_factory=list)


def build_preview(
    parsed_data: ParsedProductData,
    mapper: Optional[ManufacturerDataMapper] = None
) -> ImportPreview:
    """
    Build preview of import with diff view for existing items.
    
    Args:
        parsed_data: Parsed product data
        mapper: Optional mapper instance (will create if not provided)
        
    Returns:
        ImportPreview with all diff and creation information
    """
    if mapper is None:
        mapper = ManufacturerDataMapper()
    
    preview = ImportPreview(status="new", parsed_data=parsed_data)
    
    # Check for missing critical fields
    if not parsed_data.product_name:
        preview.missing_critical.append("product_name")
    if not parsed_data.sku:
        preview.missing_critical.append("sku")
    if not parsed_data.brand:
        preview.missing_critical.append("brand")
    
    # Check for existing product by SKU+brand
    if parsed_data.sku and parsed_data.brand:
        try:
            from toolanalysis.models import Brands
            brand = Brands.objects.get(name=parsed_data.brand)
            existing_product = Products.objects.filter(sku=parsed_data.sku, brand=brand).first()
            existing_component = Components.objects.filter(sku=parsed_data.sku, brand=brand).first()
            
            if existing_product or existing_component:
                preview.status = "update"
                preview.existing_product = existing_product
                preview.existing_component = existing_component
                
                # Build diff for component
                if existing_component:
                    preview.field_diffs.extend(_build_component_diffs(existing_component, parsed_data, mapper))
                
                # Build diff for product
                if existing_product:
                    preview.field_diffs.extend(_build_product_diffs(existing_product, parsed_data))
                
                # Check for conflicts (different name for same SKU)
                if existing_component and existing_component.name != parsed_data.product_name:
                    preview.warnings.append(
                        f"Existing component '{existing_component.name}' has different name than parsed '{parsed_data.product_name}'"
                    )
                if existing_product and existing_product.name != parsed_data.product_name:
                    preview.warnings.append(
                        f"Existing product '{existing_product.name}' has different name than parsed '{parsed_data.product_name}'"
                    )
        except Exception as e:
            preview.warnings.append(f"Error checking for existing items: {str(e)}")
    
    # Build preview data structures
    preview.product_data = {
        'name': parsed_data.product_name,
        'sku': parsed_data.sku,
        'brand': parsed_data.brand,
        'description': parsed_data.description,
        'image': parsed_data.image_url,
    }
    
    preview.component_data = {
        'name': parsed_data.product_name,
        'sku': parsed_data.sku,
        'brand': parsed_data.brand,
        'description': parsed_data.description,
        'image': parsed_data.image_url,
    }
    
    # Map included items to component previews
    for item_name in parsed_data.included_items:
        # Clean item name
        item_name = item_name.strip()
        if item_name and len(item_name) > 3:
            preview.included_components.append({
                'name': item_name,
                'sku': f"{parsed_data.sku}-{item_name[:10].upper().replace(' ', '-')}" if parsed_data.sku else "",
                'will_create': True,
            })
    
    # Product Specifications (from Gemini mapping)
    from toolanalysis.models import ProductSpecifications
    product_specs = getattr(parsed_data, '_product_specifications', [])
    if not product_specs:
        # Fallback: create from raw specifications dict
        product_specs = [
            {'name': key, 'value': value}
            for key, value in parsed_data.specifications.items()
        ]
    
    for spec in product_specs:
        spec_name = spec.get('name', '') if isinstance(spec, dict) else ''
        spec_value = spec.get('value', '') if isinstance(spec, dict) else str(spec)
        
        will_create = True
        existing_value = None
        if preview.existing_product:
            existing_spec = ProductSpecifications.objects.filter(
                product=preview.existing_product,
                name=spec_name
            ).first()
            if existing_spec:
                will_create = False
                existing_value = existing_spec.value
                if existing_value == spec_value:
                    continue
        
        preview.product_specifications.append({
            'name': spec_name,
            'value': spec_value,
            'will_create': will_create,
            'existing_value': existing_value,
        })
    
    # Component Attributes (from Gemini mapping with matched attribute names)
    from toolanalysis.models import Attributes, ComponentAttributes
    component_attrs = getattr(parsed_data, '_component_attributes', [])
    if not component_attrs:
        # Fallback: use old mapping logic
        for spec_key, spec_value in parsed_data.specifications.items():
            attribute, normalized_value = mapper.map_specification_to_attribute(
                spec_key, spec_value, {'product_name': parsed_data.product_name}
            )
            component_attrs.append({
                'attribute_name': attribute.name,
                'value': normalized_value,
                'warning': '',
            })
    
    for attr_data in component_attrs:
        attr_name = attr_data.get('attribute_name', '') if isinstance(attr_data, dict) else ''
        attr_value = attr_data.get('value', '') if isinstance(attr_data, dict) else ''
        warning = attr_data.get('warning', '') if isinstance(attr_data, dict) else ''
        
        # Try to find existing attribute by name
        attribute = None
        if attr_name and not attr_name.startswith('WARNING:'):
            try:
                attribute = Attributes.objects.get(name=attr_name)
            except Attributes.DoesNotExist:
                warning = f"Attribute '{attr_name}' not found in database"
        
        will_create = True
        existing_value = None
        if preview.existing_component and attribute:
            existing_attr = ComponentAttributes.objects.filter(
                component=preview.existing_component,
                attribute=attribute
            ).first()
            if existing_attr:
                will_create = False
                existing_value = existing_attr.value
                if existing_value == attr_value:
                    continue
        
        preview.component_attributes.append({
            'attribute_name': attr_name,
            'attribute_id': str(attribute.id) if attribute else None,
            'value': attr_value,
            'warning': warning,
            'will_create': will_create,
            'existing_value': existing_value,
        })
        # Legacy compatibility
        preview.attributes.append({
            'attribute_name': attr_name,
            'value': attr_value,
            'will_create': will_create,
            'existing_value': existing_value,
            'warning': warning,
        })
    
    # Component Features (from Gemini mapping with matched feature names)
    from toolanalysis.models import Features, ComponentFeatures
    component_feats = getattr(parsed_data, '_component_features', [])
    if not component_feats:
        # Fallback: use raw features list
        for feature_text in parsed_data.features:
            feature_name = feature_text.split(':')[0].split('.')[0].strip()
            if len(feature_name) > 50:
                feature_name = feature_name[:50]
            if not feature_name:
                feature_name = feature_text[:50]
            component_feats.append({
                'feature_name': feature_name,
                'value': feature_text,
                'warning': '',
            })
    
    for feat_data in component_feats:
        feat_name = feat_data.get('feature_name', '') if isinstance(feat_data, dict) else ''
        feat_value = feat_data.get('value', '') if isinstance(feat_data, dict) else str(feat_data)
        warning = feat_data.get('warning', '') if isinstance(feat_data, dict) else ''
        
        # Try to find existing feature by name
        feature = None
        if feat_name and not feat_name.startswith('WARNING:'):
            try:
                feature = Features.objects.get(name=feat_name)
            except Features.DoesNotExist:
                warning = f"Feature '{feat_name}' not found in database"
        
        will_create = True
        existing_value = None
        if preview.existing_component and feature:
            existing_feat = ComponentFeatures.objects.filter(
                component=preview.existing_component,
                feature=feature
            ).first()
            if existing_feat:
                will_create = False
                existing_value = existing_feat.value
                if existing_value == feat_value:
                    continue
        
        preview.component_features.append({
            'feature_name': feat_name,
            'feature_id': str(feature.id) if feature else None,
            'value': feat_value,
            'warning': warning,
            'will_create': will_create,
            'existing_value': existing_value,
        })
        # Legacy compatibility
        preview.features.append({
            'name': feat_name,
            'value': feat_value,
            'will_create': will_create,
            'existing_value': existing_value,
            'warning': warning,
        })
    
    # Categories, Subcategories, ItemTypes (from Gemini mapping)
    from toolanalysis.models import Categories, Subcategories, ItemTypes
    
    # Categories
    category_mappings = getattr(parsed_data, '_category_mappings', [])
    if not category_mappings:
        category_mappings = [{'name': cat, 'warning': ''} for cat in parsed_data.categories]
    
    for cat_data in category_mappings:
        cat_name = cat_data.get('name', '') if isinstance(cat_data, dict) else str(cat_data)
        warning = cat_data.get('warning', '') if isinstance(cat_data, dict) else ''
        
        category = None
        if cat_name and not cat_name.startswith('WARNING:'):
            try:
                category = Categories.objects.get(name=cat_name)
            except Categories.DoesNotExist:
                try:
                    category = Categories.objects.get(fullname=cat_name)
                except Categories.DoesNotExist:
                    warning = f"Category '{cat_name}' not found in database"
        
        preview.categories.append({
            'name': cat_name,
            'category_id': str(category.id) if category else None,
            'warning': warning,
        })
    
    # Subcategories
    subcategory_mappings = getattr(parsed_data, '_subcategory_mappings', [])
    for sub_data in subcategory_mappings:
        sub_name = sub_data.get('name', '') if isinstance(sub_data, dict) else str(sub_data)
        warning = sub_data.get('warning', '') if isinstance(sub_data, dict) else ''
        
        subcategory = None
        if sub_name and not sub_name.startswith('WARNING:'):
            try:
                subcategory = Subcategories.objects.get(name=sub_name)
            except Subcategories.DoesNotExist:
                try:
                    subcategory = Subcategories.objects.get(fullname=sub_name)
                except Subcategories.DoesNotExist:
                    warning = f"Subcategory '{sub_name}' not found in database"
        
        preview.subcategories.append({
            'name': sub_name,
            'subcategory_id': str(subcategory.id) if subcategory else None,
            'warning': warning,
        })
    
    # ItemTypes
    itemtype_mappings = getattr(parsed_data, '_itemtype_mappings', [])
    for it_data in itemtype_mappings:
        it_name = it_data.get('name', '') if isinstance(it_data, dict) else str(it_data)
        warning = it_data.get('warning', '') if isinstance(it_data, dict) else ''
        
        itemtype = None
        if it_name and not it_name.startswith('WARNING:'):
            try:
                itemtype = ItemTypes.objects.get(name=it_name)
            except ItemTypes.DoesNotExist:
                try:
                    itemtype = ItemTypes.objects.get(fullname=it_name)
                except ItemTypes.DoesNotExist:
                    warning = f"ItemType '{it_name}' not found in database"
        
        preview.itemtypes.append({
            'name': it_name,
            'itemtype_id': str(itemtype.id) if itemtype else None,
            'warning': warning,
        })
    
    # Count what will be created
    preview.will_create = {
        'product': 0 if preview.existing_product else 1,
        'component': 0 if preview.existing_component else 1,
        'included_components': len(preview.included_components),
        'product_specifications': len([s for s in preview.product_specifications if s.get('will_create', True)]),
        'component_attributes': len([a for a in preview.component_attributes if a.get('will_create', True)]),
        'component_features': len([f for f in preview.component_features if f.get('will_create', True)]),
        'categories': len(preview.categories),
        'subcategories': len(preview.subcategories),
        'itemtypes': len(preview.itemtypes),
        # Legacy counts
        'attributes': len([a for a in preview.component_attributes if a.get('will_create', True)]),
        'features': len([f for f in preview.component_features if f.get('will_create', True)]),
    }
    
    return preview


def _build_component_diffs(existing: Components, parsed: ParsedProductData, mapper: ManufacturerDataMapper) -> List[FieldDiff]:
    """Build field diffs for component."""
    diffs = []
    
    fields_to_compare = [
        ('name', 'product_name'),
        ('sku', 'sku'),
        ('description', 'description'),
        ('image', 'image_url'),
    ]
    
    for model_field, parsed_field in fields_to_compare:
        old_val = str(getattr(existing, model_field, '')) if getattr(existing, model_field, None) else ''
        new_val = str(getattr(parsed, parsed_field, '')) if getattr(parsed, parsed_field, None) else ''
        
        if old_val != new_val and new_val:  # Only show if new value is different and non-empty
            diffs.append(FieldDiff(
                field_name=model_field,
                old_value=old_val,
                new_value=new_val,
                changed=True
            ))
    
    return diffs


def _build_product_diffs(existing: Products, parsed: ParsedProductData) -> List[FieldDiff]:
    """Build field diffs for product."""
    diffs = []
    
    fields_to_compare = [
        ('name', 'product_name'),
        ('sku', 'sku'),
        ('description', 'description'),
        ('image', 'image_url'),
    ]
    
    for model_field, parsed_field in fields_to_compare:
        old_val = str(getattr(existing, model_field, '')) if getattr(existing, model_field, None) else ''
        new_val = str(getattr(parsed, parsed_field, '')) if getattr(parsed, parsed_field, None) else ''
        
        if old_val != new_val and new_val:
            diffs.append(FieldDiff(
                field_name=model_field,
                old_value=old_val,
                new_value=new_val,
                changed=True
            ))
    
    return diffs

