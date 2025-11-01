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
    
    # Map specifications to attributes
    for spec_key, spec_value in parsed_data.specifications.items():
        attribute, normalized_value = mapper.map_specification_to_attribute(
            spec_key, spec_value, {'product_name': parsed_data.product_name}
        )
        preview.attributes.append({
            'attribute_name': attribute.name,
            'value': normalized_value,
            'will_create': True,
        })
    
    # Map features
    for feature_text in parsed_data.features:
        # Extract feature name (first part before colon or first sentence)
        feature_name = feature_text.split(':')[0].split('.')[0].strip()
        if len(feature_name) > 50:
            feature_name = feature_name[:50]
        if not feature_name:
            feature_name = feature_text[:50]
        
        preview.features.append({
            'name': feature_name,
            'value': feature_text,
            'will_create': True,
        })
    
    # Count what will be created
    preview.will_create = {
        'product': 0 if preview.existing_product else 1,
        'component': 0 if preview.existing_component else 1,
        'included_components': len(preview.included_components),
        'attributes': len(preview.attributes),
        'features': len(preview.features),
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

