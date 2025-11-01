"""Manufacturer URL import system for automatically populating product and component data."""

from .base import ManufacturerParser, ParsedProductData
from .registry import get_parser_for_url, get_parser_for_brand, MANUFACTURER_PARSERS, register_parser
from .dewalt import DewaltParser

# Register parsers
register_parser('DEWALT', DewaltParser)

# Import all services
from .mapper import ManufacturerDataMapper
from .preview import build_preview, ImportPreview, FieldDiff
from .importer import execute_import, ImportResult
from .gemini_helper import GeminiDataEnhancer

__all__ = [
    "ManufacturerParser",
    "ParsedProductData",
    "get_parser_for_url",
    "get_parser_for_brand",
    "MANUFACTURER_PARSERS",
    "register_parser",
    "DewaltParser",
    "ManufacturerDataMapper",
    "build_preview",
    "ImportPreview",
    "FieldDiff",
    "execute_import",
    "ImportResult",
    "GeminiDataEnhancer",
]
