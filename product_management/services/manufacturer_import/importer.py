"""Import execution service."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from django.db import transaction

from toolanalysis.models import (
    Attributes, BatteryVoltages, Brands, Categories, ComponentAttributes,
    ComponentFeatures, Components, Features, ItemTypes, MotorTypes,
    ProductComponents, Products, Statuses,
)

from product_management.models import BackofficeAudit
from product_management.services.audit import record_audit_entry

from .mapper import ManufacturerDataMapper
from .preview import ImportPreview


@dataclass
class ImportResult:
    """Result of import operation."""
    product: Products
    component: Components
    included_components: List[Components]
    attributes_created: int
    features_created: int
    was_update: bool
    updated_fields: List[str]


@transaction.atomic
def execute_import(
    preview: ImportPreview,
    user=None
) -> ImportResult:
    """
    Execute the import, creating/updating all entities.
    
    Args:
        preview: ImportPreview with all data to import
        user: User performing the import
        
    Returns:
        ImportResult with created/updated entities and counts
    """
    if not preview.parsed_data:
        raise ValueError("Preview must have parsed_data")
    
    parsed_data = preview.parsed_data
    mapper = ManufacturerDataMapper()
    
    # Get or create brand
    brand, _ = Brands.objects.get_or_create(name=parsed_data.brand)
    
    # Get status
    status, _ = Statuses.objects.get_or_create(name="Active", defaults={"sortorder": 1})
    
    # Create or update main component
    component_payload = {
        'name': parsed_data.product_name,
        'sku': parsed_data.sku,
        'brand': brand,
        'description': parsed_data.description or '',
        'image': parsed_data.image_url or '',
        'isaccessory': False,
        'is_featured': False,
    }
    
    # Add motor type if identified
    motor_type = mapper.identify_motor_type(parsed_data.specifications, parsed_data.description)
    if motor_type:
        component_payload['motortype'] = motor_type
    
    # Add battery info
    battery_voltage, battery_platform = mapper.extract_battery_info(parsed_data.specifications)
    
    if preview.existing_component:
        # Update existing component - only changed fields
        component = preview.existing_component
        updated_fields = []
        for diff in preview.field_diffs:
            if diff.field_name in component_payload and diff.changed:
                setattr(component, diff.field_name, component_payload[diff.field_name])
                updated_fields.append(diff.field_name)
        if motor_type and component.motortype != motor_type:
            component.motortype = motor_type
            updated_fields.append('motortype')
        component.save()
        was_update = True
    else:
        # Create new component
        component = Components.objects.create(**component_payload)
        if battery_voltage:
            component.batteryvoltages.add(battery_voltage)
        was_update = False
        updated_fields = []
    
    # Add categories and item types
    categories = mapper.map_categories(parsed_data)
    component.categories.set(categories)
    
    item_types = mapper.map_item_types(parsed_data)
    component.itemtypes.set(item_types)
    
    # Create/update component attributes
    attributes_created = 0
    for spec_key, spec_value in parsed_data.specifications.items():
        attribute, normalized_value = mapper.map_specification_to_attribute(
            spec_key, spec_value, {'product_name': parsed_data.product_name}
        )
        ComponentAttributes.objects.update_or_create(
            component=component,
            attribute=attribute,
            defaults={'value': normalized_value}
        )
        attributes_created += 1
    
    # Create/update component features
    features_created = 0
    for feature_text in parsed_data.features:
        # Extract feature name
        feature_name = feature_text.split(':')[0].split('.')[0].strip()
        if len(feature_name) > 50:
            feature_name = feature_name[:50]
        if not feature_name:
            feature_name = feature_text[:50]
        
        feature, _ = Features.objects.get_or_create(
            name=feature_name,
            defaults={'sortorder': 0}
        )
        
        ComponentFeatures.objects.update_or_create(
            component=component,
            feature=feature,
            defaults={'value': feature_text}
        )
        component.features.add(feature)
        features_created += 1
    
    # Create included items as components
    included_components = []
    for item_name in parsed_data.included_items:
        # Clean item name
        item_name = item_name.strip()
        if not item_name or len(item_name) < 3:
            continue
        
        # Generate SKU for included item
        item_sku = f"{parsed_data.sku}-{item_name[:10].upper().replace(' ', '-')}" if parsed_data.sku else ""
        
        included_component, created = Components.objects.get_or_create(
            brand=brand,
            name=item_name,
            defaults={
                'sku': item_sku,
                'isaccessory': True,
                'description': f"Included with {parsed_data.product_name}"
            }
        )
        included_components.append(included_component)
    
    # Create or update product
    product_payload = {
        'name': parsed_data.product_name,
        'sku': parsed_data.sku,
        'brand': brand,
        'description': parsed_data.description or '',
        'image': parsed_data.image_url or '',
        'status': status,
        'isaccessory': False,
    }
    
    if preview.existing_product:
        # Update existing product
        product = preview.existing_product
        for diff in preview.field_diffs:
            if diff.field_name in product_payload and diff.changed:
                setattr(product, diff.field_name, product_payload[diff.field_name])
        product.save()
    else:
        # Create new product
        product = Products.objects.create(**product_payload)
    
    # Link main component to product
    ProductComponents.objects.get_or_create(
        product=product,
        component=component,
        defaults={'quantity': 1}
    )
    
    # Link included components to product
    for included_component in included_components:
        ProductComponents.objects.get_or_create(
            product=product,
            component=included_component,
            defaults={'quantity': 1}
        )
    
    # Record audit entries
    record_audit_entry(BackofficeAudit.ENTITY_PRODUCT, product, "create" if not preview.existing_product else "update", user=user)
    record_audit_entry(BackofficeAudit.ENTITY_COMPONENT, component, "create" if not preview.existing_component else "update", user=user)
    
    return ImportResult(
        product=product,
        component=component,
        included_components=included_components,
        attributes_created=attributes_created,
        features_created=features_created,
        was_update=was_update,
        updated_fields=updated_fields if preview.existing_component else []
    )

