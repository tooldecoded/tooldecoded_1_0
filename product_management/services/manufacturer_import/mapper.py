"""Data mapper to convert ParsedProductData to Django models."""

import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction

from toolanalysis.models import (
    Attributes, BatteryPlatforms, BatteryVoltages, Brands, Categories,
    Components, Features, ItemTypes, MotorTypes, Statuses, Subcategories,
)

from .base import ParsedProductData
from .gemini_helper import GeminiDataEnhancer


class ManufacturerDataMapper:
    """Maps parsed manufacturer data to Django model instances."""
    
    def __init__(self, use_gemini: bool = True):
        self.gemini = GeminiDataEnhancer() if use_gemini else None
    
    def map_specification_to_attribute(self, spec_key: str, spec_value: str, context: Dict = None) -> Tuple[Attributes, str]:
        """
        Normalize and map specification key to Attribute model.
        
        Args:
            spec_key: Raw specification key from manufacturer
            spec_value: Specification value
            context: Additional context (product name, brand, etc.)
            
        Returns:
            Tuple of (Attribute instance, normalized value)
        """
        # Use Gemini if available for normalization
        normalized_name = spec_key
        if self.gemini:
            normalized_name = self.gemini.normalize_attribute_name(spec_key, spec_value, context or {})
        
        # Fallback to rule-based normalization
        if normalized_name == spec_key:
            normalized_name = self._normalize_attribute_name_rule_based(spec_key)
        
        # Get or create attribute
        attribute, _ = Attributes.objects.get_or_create(
            name=normalized_name,
            defaults={'sortorder': 0}
        )
        
        # Normalize value (remove units from key, keep in value if needed)
        normalized_value = self._normalize_attribute_value(spec_value, spec_key)
        
        return attribute, normalized_value
    
    def _normalize_attribute_name_rule_based(self, spec_key: str) -> str:
        """Rule-based attribute name normalization."""
        # Common patterns
        patterns = {
            r'\[.*?\]': '',  # Remove brackets and contents
            r'\s+': ' ',     # Normalize whitespace
        }
        
        normalized = spec_key.strip()
        for pattern, replacement in patterns.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Specific mappings
        mappings = {
            'MWO': 'Max Power',
            'No Load Speed': 'Speed',
            'Speed \[rpm\]': 'Speed',
            'Has LED Light\?': 'LED Light',
            'Is Brushless\?': 'Brushless',
            'Has Variable Speed\?': 'Variable Speed',
            'Chuck Size': 'Chuck Size',
            'Product Weight': 'Weight',
            'Product Length': 'Length',
            'Product Width': 'Width',
            'Tool Length': 'Length',
            'Voltage': 'Voltage',
        }
        
        for pattern, replacement in mappings.items():
            if re.search(pattern, normalized, re.IGNORECASE):
                normalized = replacement
                break
        
        return normalized.strip()
    
    def _normalize_attribute_value(self, value: str, spec_key: str) -> str:
        """Normalize attribute value, preserving units when appropriate."""
        # Clean up common formatting
        value = value.strip()
        
        # Extract numeric values with units
        # For things like "0-450/0-1650", keep as-is
        # For "Yes/No", convert to boolean-like strings
        if value.lower() in ['yes', 'true', '1']:
            return 'Yes'
        elif value.lower() in ['no', 'false', '0']:
            return 'No'
        
        return value
    
    def extract_battery_info(self, specs: Dict[str, str]) -> Tuple[Optional[BatteryVoltages], Optional[BatteryPlatforms]]:
        """
        Extract battery voltage and platform from specifications.
        
        Returns:
            Tuple of (BatteryVoltages instance or None, BatteryPlatforms instance or None)
        """
        voltage = None
        platform = None
        
        # Look for voltage in various spec keys
        voltage_patterns = [
            r'voltage',
            r'battery.*voltage',
            r'voltage.*\[v\]',
        ]
        
        voltage_value = None
        for key, value in specs.items():
            if any(re.search(pattern, key, re.IGNORECASE) for pattern in voltage_patterns):
                # Extract numeric voltage value
                voltage_match = re.search(r'(\d+\.?\d*)', value)
                if voltage_match:
                    try:
                        voltage_value = float(voltage_match.group(1))
                        break
                    except ValueError:
                        pass
        
        # Also check product name for voltage (e.g., "20V MAX")
        if not voltage_value:
            # This would need to be passed from parsed_data, but for now check specs
            for value in specs.values():
                voltage_match = re.search(r'(\d+)\s*v\s*(?:max|volt)', value, re.IGNORECASE)
                if voltage_match:
                    try:
                        voltage_value = float(voltage_match.group(1))
                        break
                    except ValueError:
                        pass
        
        if voltage_value:
            voltage, _ = BatteryVoltages.objects.get_or_create(value=voltage_value)
        
        # Extract platform from product name or specs
        # DEWALT: "20V MAX", "60V MAX", "12V MAX"
        # This would be better done with context from parsed_data
        # For now, create platform based on voltage if found
        
        return voltage, platform
    
    def identify_motor_type(self, specs: Dict[str, str], description: str = "") -> Optional[MotorTypes]:
        """Identify motor type from specifications and description."""
        # Check if brushless is mentioned
        brushless_indicators = ['brushless', 'brush-less']
        
        for key, value in specs.items():
            if 'brushless' in key.lower() and value.lower() in ['yes', 'true', '1']:
                motor_type, _ = MotorTypes.objects.get_or_create(
                    name='Brushless',
                    defaults={'sortorder': 0}
                )
                return motor_type
        
        # Check description
        text_to_check = description.lower()
        for indicator in brushless_indicators:
            if indicator in text_to_check:
                motor_type, _ = MotorTypes.objects.get_or_create(
                    name='Brushless',
                    defaults={'sortorder': 0}
                )
                return motor_type
        
        return None
    
    def map_categories(self, parsed_data: ParsedProductData, existing_categories: List[str] = None) -> List[Categories]:
        """
        Map product to appropriate Categories.
        
        Args:
            parsed_data: ParsedProductData object
            existing_categories: Categories already found from breadcrumb
            
        Returns:
            List of Category instances
        """
        categories = []
        
        # Use Gemini if available for intelligent mapping
        if self.gemini and not parsed_data.categories:
            suggested = self.gemini.map_categories(
                parsed_data.product_name,
                parsed_data.description,
                parsed_data.specifications
            )
            parsed_data.categories.extend(suggested)
        
        # Get or create categories
        for cat_name in parsed_data.categories:
            if cat_name and cat_name.strip():
                cat_name_clean = cat_name.strip()
                # Categories model requires fullname to be unique, use name as fullname if not provided
                category, _ = Categories.objects.get_or_create(
                    fullname=cat_name_clean,
                    defaults={'name': cat_name_clean}
                )
                categories.append(category)
        
        return categories
    
    def map_item_types(self, parsed_data: ParsedProductData) -> List[ItemTypes]:
        """
        Map product to appropriate ItemTypes based on categories and description.
        
        Returns:
            List of ItemTypes instances
        """
        item_types = []
        
        # Map common category patterns to item types
        category_to_itemtype = {
            'drills': 'Drill Drivers',
            'drill drivers': 'Drill Drivers',
            'impact drivers': 'Impact Drivers',
            'impact wrenches': 'Impact Wrenches',
            'circular saws': 'Circular Saws',
            'reciprocating saws': 'Reciprocating Saws',
            'multitools': 'Multi-Tools',
        }
        
        # Check categories
        categories_lower = [cat.lower() for cat in parsed_data.categories]
        for cat_lower in categories_lower:
            if cat_lower in category_to_itemtype:
                item_type_name = category_to_itemtype[cat_lower]
                item_type, _ = ItemTypes.objects.get_or_create(
                    name=item_type_name,
                    defaults={}
                )
                if item_type not in item_types:
                    item_types.append(item_type)
        
        # Also check product name/description
        text_to_check = (parsed_data.product_name + " " + parsed_data.description).lower()
        for keyword, item_type_name in category_to_itemtype.items():
            if keyword in text_to_check:
                item_type, _ = ItemTypes.objects.get_or_create(
                    name=item_type_name,
                    defaults={}
                )
                if item_type not in item_types:
                    item_types.append(item_type)
        
        return item_types

