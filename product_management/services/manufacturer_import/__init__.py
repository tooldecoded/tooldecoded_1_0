"""Manufacturer URL import system for automatically populating product and component data."""

from .base import ManufacturerParser, ParsedProductData
from .registry import get_parser_for_brand
from .generic_parser import GenericManufacturerParser

# Import all services
from .mapper import ManufacturerDataMapper
from .preview import build_preview, ImportPreview, FieldDiff
from .importer import execute_import, ImportResult
from .gemini_helper import GeminiDataEnhancer

__all__ = [
    "ManufacturerParser",
    "ParsedProductData",
    "get_parser_for_brand",
    "GenericManufacturerParser",
    "ManufacturerDataMapper",
    "build_preview",
    "ImportPreview",
    "FieldDiff",
    "execute_import",
    "ImportResult",
    "GeminiDataEnhancer",
]
