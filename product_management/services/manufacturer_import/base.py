"""Base parser interface for manufacturer product page parsing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParsedProductData:
    """Structured data extracted from a manufacturer product page."""
    
    product_name: str = ""
    sku: str = ""
    brand: str = ""
    description: str = ""
    specifications: Dict[str, str] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    included_items: List[str] = field(default_factory=list)
    image_url: str = ""
    categories: List[str] = field(default_factory=list)
    source_url: str = ""
    parsing_errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add a parsing error message."""
        self.parsing_errors.append(error)
    
    def is_valid(self) -> bool:
        """Check if critical fields are present."""
        return bool(self.product_name and self.sku and self.brand)


class ManufacturerParser(ABC):
    """Abstract base class for manufacturer-specific parsers."""
    
    @abstractmethod
    def parse(self, url: str) -> ParsedProductData:
        """
        Parse a manufacturer product page URL and extract product data.
        
        Args:
            url: The product page URL to parse
            
        Returns:
            ParsedProductData containing all extractable information
            
        Raises:
            ValueError: If URL is invalid or parsing fails critically
        """
        pass
    
    @abstractmethod
    def detect_manufacturer(self, url: str) -> str:
        """
        Identify the manufacturer from a URL.
        
        Args:
            url: The product page URL
            
        Returns:
            Manufacturer name (e.g., "DEWALT", "Milwaukee")
        """
        pass
    
    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Check if a URL is a valid format for this manufacturer.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if URL format is valid for this manufacturer
        """
        pass

