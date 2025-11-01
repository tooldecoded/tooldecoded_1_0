"""Parser registry for manufacturer-specific parsers."""

from typing import Dict, Type, Optional
from urllib.parse import urlparse

from .base import ManufacturerParser


# Registry will be populated by importing parsers
MANUFACTURER_PARSERS: Dict[str, Type[ManufacturerParser]] = {}


def register_parser(manufacturer_name: str, parser_class: Type[ManufacturerParser]) -> None:
    """Register a parser for a manufacturer."""
    MANUFACTURER_PARSERS[manufacturer_name.upper()] = parser_class


def get_parser_for_url(url: str) -> Optional[ManufacturerParser]:
    """
    Auto-detect manufacturer from URL and return appropriate parser.
    
    Args:
        url: Product page URL
        
    Returns:
        ManufacturerParser instance or None if no parser found
    """
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""
    
    # Try to detect manufacturer from domain
    hostname_lower = hostname.lower()
    
    if 'dewalt' in hostname_lower:
        return get_parser_for_brand('DEWALT')
    elif 'milwaukee' in hostname_lower:
        return get_parser_for_brand('Milwaukee')
    elif 'makita' in hostname_lower:
        return get_parser_for_brand('Makita')
    
    # Try each registered parser's detect method
    for brand_name, parser_class in MANUFACTURER_PARSERS.items():
        parser_instance = parser_class()
        if parser_instance.validate_url(url):
            return parser_instance
    
    return None


def get_parser_for_brand(brand_name: str) -> Optional[ManufacturerParser]:
    """
    Get parser by manufacturer name.
    
    Args:
        brand_name: Manufacturer name (e.g., "DEWALT")
        
    Returns:
        ManufacturerParser instance or None if not found
    """
    brand_key = brand_name.upper()
    parser_class = MANUFACTURER_PARSERS.get(brand_key)
    if parser_class:
        return parser_class()
    return None

