"""Creation workflows for the product management backoffice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from django.core.exceptions import ValidationError
from django.db import transaction

from product_management.models import BackofficeAudit
from product_management.services.audit import record_audit_entry, snapshot_instance
from toolanalysis.models import Components, ProductComponents, Products


@dataclass(frozen=True)
class BundleComponentItem:
    component: Components
    quantity: int = 1

    def __post_init__(self) -> None:  # type: ignore[override]
        if self.quantity < 1:
            raise ValidationError({"quantity": "Quantity must be at least 1."})


def _split_relations(model, data: Dict[str, Any]) -> Dict[str, Iterable[Any]]:
    relation_values: Dict[str, Iterable[Any]] = {}
    for field in model._meta.many_to_many:
        key = field.name
        if key in data:
            relation_values[key] = data.pop(key)
    return relation_values


def _apply_relations(instance, relation_values: Dict[str, Iterable[Any]]) -> None:
    for field_name, value in relation_values.items():
        manager = getattr(instance, field_name)
        manager.set(value or [])


def _normalize_sku(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _validate_unique(model, *, brand, sku: Optional[str], instance_id=None, error_key: str) -> None:
    if not brand or not sku:
        return
    qs = model.objects.filter(brand=brand, sku=sku)
    if instance_id:
        qs = qs.exclude(id=instance_id)
    if qs.exists():
        raise ValidationError({error_key: "SKU already exists for this brand."})


@transaction.atomic
def create_bare_tool(
    *,
    component_data: Dict[str, Any],
    product_data: Optional[Dict[str, Any]] = None,
    user=None,
) -> Tuple[Components, Optional[Products]]:
    """Create a component representing a bare tool and optional product shell."""

    component_payload = dict(component_data)
    component_relations = _split_relations(Components, component_payload)
    component_payload["sku"] = _normalize_sku(component_payload.get("sku"))
    _validate_unique(
        Components,
        brand=component_payload.get("brand"),
        sku=component_payload.get("sku"),
        error_key="sku",
    )

    component = Components.objects.create(**component_payload)
    _apply_relations(component, component_relations)
    record_audit_entry(BackofficeAudit.ENTITY_COMPONENT, component, "create", user=user)

    product = None
    if product_data:
        product_payload = dict(product_data)
        quantity = int(product_payload.pop("component_quantity", 1) or 1)
        product_relations = _split_relations(Products, product_payload)
        product_payload.setdefault("brand", component.brand)
        product_payload.setdefault("motortype", component.motortype)
        product_payload.setdefault("listingtype", component.listingtype)
        product_payload.setdefault("isaccessory", component.isaccessory)
        product_payload["sku"] = _normalize_sku(product_payload.get("sku"))
        
        # Default status to "Active" if not provided
        if not product_payload.get("status"):
            from toolanalysis.models import Statuses
            active_status, _ = Statuses.objects.get_or_create(name="Active", defaults={"sortorder": 1})
            product_payload["status"] = active_status
        
        _validate_unique(
            Products,
            brand=product_payload.get("brand"),
            sku=product_payload.get("sku"),
            error_key="product_sku",
        )

        product = Products.objects.create(**product_payload)
        _apply_relations(product, product_relations)
        ProductComponents.objects.create(
            product=product, component=component, quantity=max(1, quantity)
        )
        record_audit_entry(BackofficeAudit.ENTITY_PRODUCT, product, "create", user=user)

    return component, product


@transaction.atomic
def create_bundle_from_products(
    *,
    bundle_data: Dict[str, Any],
    component_items: Sequence[BundleComponentItem],
    user=None,
) -> Products:
    """Create a bundled product composed of existing components."""

    if not component_items:
        raise ValidationError({"components": "At least one component is required."})

    product_payload = dict(bundle_data)
    product_relations = _split_relations(Products, product_payload)
    product_payload["sku"] = _normalize_sku(product_payload.get("sku"))
    
    # Default status to "Active" if not provided
    if not product_payload.get("status"):
        from toolanalysis.models import Statuses
        active_status, _ = Statuses.objects.get_or_create(name="Active", defaults={"sortorder": 1})
        product_payload["status"] = active_status
    
    _validate_unique(
        Products,
        brand=product_payload.get("brand"),
        sku=product_payload.get("sku"),
        error_key="sku",
    )

    product = Products.objects.create(**product_payload)
    _apply_relations(product, product_relations)

    for item in component_items:
        ProductComponents.objects.create(
            product=product, component=item.component, quantity=item.quantity
        )

    record_audit_entry(BackofficeAudit.ENTITY_PRODUCT, product, "create", user=user)

    return product


@transaction.atomic
def extract_component_from_product(
    product_or_id: Products | str,
    *,
    overrides: Optional[Dict[str, Any]] = None,
    user=None,
) -> Components:
    """Create a component from an existing product, optionally overriding fields."""

    overrides = overrides or {}
    if isinstance(product_or_id, Products):
        product = product_or_id
    else:
        product = Products.objects.get(id=product_or_id)

    component_payload: Dict[str, Any] = {
        "name": overrides.get("name", product.name),
        "description": overrides.get("description", product.description),
        "brand": overrides.get("brand", product.brand),
        "sku": _normalize_sku(overrides.get("sku", product.sku)),
        "listingtype": overrides.get("listingtype", product.listingtype),
        "motortype": overrides.get("motortype", product.motortype),
        "image": overrides.get("image", product.image),
        "isaccessory": overrides.get("isaccessory", product.isaccessory),
        "is_featured": overrides.get("is_featured", False),
        "standalone_price": overrides.get("standalone_price"),
        "showcase_priority": overrides.get("showcase_priority", 0),
        "fair_price_narrative": overrides.get("fair_price_narrative"),
    }

    component_relations: Dict[str, Iterable[Any]] = {
        "itemtypes": overrides.get("itemtypes", product.itemtypes.all()),
        "subcategories": overrides.get("subcategories", product.subcategories.all()),
        "categories": overrides.get("categories", product.categories.all()),
        "batteryplatforms": overrides.get("batteryplatforms", product.batteryplatforms.all()),
        "batteryvoltages": overrides.get("batteryvoltages", product.batteryvoltages.all()),
        "features": overrides.get("features", product.features.all()),
        "productlines": overrides.get("productlines", []),
    }

    _validate_unique(
        Components,
        brand=component_payload.get("brand"),
        sku=component_payload.get("sku"),
        error_key="sku",
    )

    component = Components.objects.create(**component_payload)
    _apply_relations(component, component_relations)
    record_audit_entry(BackofficeAudit.ENTITY_COMPONENT, component, "create", user=user)

    return component


@transaction.atomic
def batch_update_components(
    component_ids: Sequence[str],
    updates: Dict[str, Any],
    *,
    user=None,
) -> int:
    """Batch update multiple components with the same field values."""
    
    if not component_ids:
        raise ValidationError("No component IDs provided.")
    
    components = Components.objects.filter(id__in=component_ids)
    count = components.count()
    
    if count == 0:
        raise ValidationError("No components found with the provided IDs.")
    
    # Separate M2M fields from regular fields
    m2m_updates: Dict[str, Iterable[Any]] = {}
    field_updates: Dict[str, Any] = {}
    
    m2m_field_names = {f.name for f in Components._meta.many_to_many}
    
    for key, value in updates.items():
        if value is None:
            continue  # Skip None values (means "don't change")
        
        if key in m2m_field_names:
            m2m_updates[key] = value
        else:
            field_updates[key] = value
    
    # Apply field updates
    if field_updates:
        components.update(**field_updates)
    
    # Apply M2M updates - need to refetch since update() doesn't return objects
    if m2m_updates:
        for component in Components.objects.filter(id__in=component_ids):
            for field_name, value in m2m_updates.items():
                manager = getattr(component, field_name)
                manager.set(value)
    
    # Record audit entries for each updated component
    for component in Components.objects.filter(id__in=component_ids):
        record_audit_entry(BackofficeAudit.ENTITY_COMPONENT, component, "batch_update", user=user)
    
    return count


@transaction.atomic
def batch_update_products(
    product_ids: Sequence[str],
    updates: Dict[str, Any],
    *,
    user=None,
) -> int:
    """Batch update multiple products with the same field values."""
    
    if not product_ids:
        raise ValidationError("No product IDs provided.")
    
    products = Products.objects.filter(id__in=product_ids)
    count = products.count()
    
    if count == 0:
        raise ValidationError("No products found with the provided IDs.")
    
    # Separate M2M fields from regular fields
    m2m_updates: Dict[str, Iterable[Any]] = {}
    field_updates: Dict[str, Any] = {}
    
    m2m_field_names = {f.name for f in Products._meta.many_to_many}
    
    for key, value in updates.items():
        if value is None:
            continue  # Skip None values (means "don't change")
        
        if key in m2m_field_names:
            m2m_updates[key] = value
        else:
            field_updates[key] = value
    
    # Apply field updates
    if field_updates:
        products.update(**field_updates)
    
    # Apply M2M updates - need to refetch since update() doesn't return objects
    if m2m_updates:
        for product in Products.objects.filter(id__in=product_ids):
            for field_name, value in m2m_updates.items():
                manager = getattr(product, field_name)
                manager.set(value)
    
    # Record audit entries for each updated product
    for product in Products.objects.filter(id__in=product_ids):
        record_audit_entry(BackofficeAudit.ENTITY_PRODUCT, product, "batch_update", user=user)
    
    return count

