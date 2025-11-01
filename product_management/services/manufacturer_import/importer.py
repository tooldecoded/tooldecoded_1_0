"""Import execution service."""

from dataclasses import dataclass
from typing import Dict, List, Optional

from django.db import transaction

from toolanalysis.models import (
    Attributes, BatteryVoltages, Brands, Categories, ComponentAttributes,
    ComponentFeatures, Components, Features, ItemTypes, MotorTypes,
    ProductComponents, Products, ProductSpecifications, Statuses,
    Subcategories,
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
    
    # Use edited values if available (from form), otherwise use parsed data
    component_name = getattr(parsed_data, '_component_name', None) or parsed_data.product_name
    component_sku = getattr(parsed_data, '_component_sku', None) or parsed_data.sku
    component_description = getattr(parsed_data, '_component_description', None) or parsed_data.description or ''
    component_image = getattr(parsed_data, '_component_image_url', None) or parsed_data.image_url or ''
    
    # Create or update main component
    component_payload = {
        'name': component_name,
        'sku': component_sku,
        'brand': brand,
        'description': component_description,
        'image': component_image,
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
    
    # Add categories, subcategories, and item types from preview (edited values)
    # Categories
    category_ids = []
    for cat_data in preview.categories:
        cat_id = cat_data.get('category_id')
        if cat_id:
            try:
                category = Categories.objects.get(id=cat_id)
                category_ids.append(category.id)
            except Categories.DoesNotExist:
                pass
    
    # Subcategories
    subcategory_ids = []
    for sub_data in preview.subcategories:
        sub_id = sub_data.get('subcategory_id')
        if sub_id:
            try:
                subcategory = Subcategories.objects.get(id=sub_id)
                subcategory_ids.append(subcategory.id)
            except Subcategories.DoesNotExist:
                pass
    
    # ItemTypes
    itemtype_ids = []
    for it_data in preview.itemtypes:
        it_id = it_data.get('itemtype_id')
        if it_id:
            try:
                itemtype = ItemTypes.objects.get(id=it_id)
                itemtype_ids.append(itemtype.id)
            except ItemTypes.DoesNotExist:
                pass
    
    component.categories.set(category_ids)
    component.subcategories.set(subcategory_ids)
    component.itemtypes.set(itemtype_ids)
    
    # Create/update ProductSpecifications (from preview)
    product_specs_created = 0
    for spec_data in preview.product_specifications:
        spec_name = spec_data.get('name', '').strip()
        spec_value = spec_data.get('value', '').strip()
        if spec_name:
            ProductSpecifications.objects.update_or_create(
                product=product,
                name=spec_name,
                defaults={'value': spec_value}
            )
            product_specs_created += 1
    
    # Create/update ComponentAttributes (from preview with matched attributes)
    attributes_created = 0
    for attr_data in preview.component_attributes:
        attr_name = attr_data.get('attribute_name', '').strip()
        attr_value = attr_data.get('value', '').strip()
        
        # Skip warnings
        if not attr_name or attr_name.startswith('WARNING:'):
            continue
        
        # Get or create attribute
        attribute = None
        attr_id = attr_data.get('attribute_id')
        if attr_id:
            try:
                attribute = Attributes.objects.get(id=attr_id)
            except Attributes.DoesNotExist:
                pass
        
        if not attribute:
            # Try to find by name
            try:
                attribute = Attributes.objects.get(name=attr_name)
            except Attributes.DoesNotExist:
                # Create new attribute if it doesn't exist
                attribute = Attributes.objects.create(name=attr_name, sortorder=0)
        
        if attribute and attr_value:
            ComponentAttributes.objects.update_or_create(
                component=component,
                attribute=attribute,
                defaults={'value': attr_value}
            )
            attributes_created += 1
    
    # Create/update ComponentFeatures (from preview with matched features)
    features_created = 0
    for feat_data in preview.component_features:
        feat_name = feat_data.get('feature_name', '').strip()
        feat_value = feat_data.get('value', '').strip()
        
        # Skip warnings
        if not feat_name or feat_name.startswith('WARNING:'):
            continue
        
        # Get or create feature
        feature = None
        feat_id = feat_data.get('feature_id')
        if feat_id:
            try:
                feature = Features.objects.get(id=feat_id)
            except Features.DoesNotExist:
                pass
        
        if not feature:
            # Try to find by name
            try:
                feature = Features.objects.get(name=feat_name)
            except Features.DoesNotExist:
                # Create new feature if it doesn't exist
                feature = Features.objects.create(name=feat_name, sortorder=0)
        
        if feature and feat_value:
            ComponentFeatures.objects.update_or_create(
                component=component,
                feature=feature,
                defaults={'value': feat_value}
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
    
    # Use edited product values if available, otherwise use parsed data
    product_name = getattr(parsed_data, '_product_name', None) or parsed_data.product_name
    product_sku = getattr(parsed_data, '_product_sku', None) or parsed_data.sku
    product_description = getattr(parsed_data, '_product_description', None) or parsed_data.description or ''
    product_image = getattr(parsed_data, '_product_image_url', None) or parsed_data.image_url or ''
    
    # Create or update product
    product_payload = {
        'name': product_name,
        'sku': product_sku,
        'brand': brand,
        'description': product_description,
        'image': product_image,
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
    
    # Also set categories, subcategories, itemtypes for product
    product.categories.set(category_ids)
    product.subcategories.set(subcategory_ids)
    product.itemtypes.set(itemtype_ids)
    
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

