"""Parser registry for manufacturer parsers."""

from typing import Optional

from .base import ManufacturerParser
from .generic_parser import GenericManufacturerParser


def get_parser_for_brand(brand_name: str) -> Optional[ManufacturerParser]:
    """
    Get parser for a manufacturer brand.
    
    Args:
        brand_name: Manufacturer name (e.g., "DEWALT", "Milwaukee")
        
    Returns:
        GenericManufacturerParser instance configured for the brand
    """
    if brand_name:
        return GenericManufacturerParser(brand=brand_name)
    return None

