"""Service layer entry points for the product management backoffice."""

from .audit import undo_last_change
from .creation import (
    BundleComponentItem,
    batch_update_components,
    batch_update_products,
    create_bare_tool,
    create_bundle_from_products,
    extract_component_from_product,
)

__all__ = [
    "BundleComponentItem",
    "batch_update_components",
    "batch_update_products",
    "create_bare_tool",
    "create_bundle_from_products",
    "extract_component_from_product",
    "undo_last_change",
]

