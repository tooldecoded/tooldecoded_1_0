"""Gemini-based HTML parser using file API for extracting product data."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings

from toolanalysis.models import Attributes, Categories, Features, ItemTypes, Subcategories

from .base import ParsedProductData


class GeminiHTMLParser:
    """Parse HTML product pages using Gemini File API."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not self.api_key:
            # Fallback to the API key from gemini.py script if available
            self.api_key = "AIzaSyCBU440DFi_w0L77QPpCKpO319nSU1hLBY"
        
        self.model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash-exp')
    
    def parse_html(self, html: str, brand: str, source_url: str = "") -> ParsedProductData:
        """
        Parse HTML using Gemini File API.
        
        Args:
            html: HTML source code
            brand: Manufacturer brand name
            source_url: Optional source URL for reference
            
        Returns:
            ParsedProductData with extracted information
        """
        data = ParsedProductData(source_url=source_url or "file:///pasted-html", brand=brand)
        
        if not self.api_key:
            data.add_error("Gemini API key not configured")
            return data
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            # Create temporary files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save HTML to file
                html_file_path = os.path.join(temp_dir, 'product_page.html')
                with open(html_file_path, 'w', encoding='utf-8') as f:
                    f.write(html)
                
                # Get models.py structure
                models_structure = self._get_models_structure()
                models_file_path = os.path.join(temp_dir, 'models_structure.txt')
                with open(models_file_path, 'w', encoding='utf-8') as f:
                    f.write(models_structure)
                
                # Upload files to Gemini
                html_file = genai.upload_file(path=html_file_path, display_name="Product Page HTML")
                models_file = genai.upload_file(path=models_file_path, display_name="Models Structure")
                
                # Wait for files to be processed
                import time
                files_to_check = [('html', html_file), ('models', models_file)]
                processed_files = []
                
                for file_type, file in files_to_check:
                    # Wait for file to be processed
                    while file.state.name == "PROCESSING":
                        time.sleep(2)
                        file = genai.get_file(file.name)
                    
                    if file.state.name == "FAILED":
                        data.add_error(f"File upload failed: {file_type} file")
                        # Try to clean up
                        try:
                            genai.delete_file(file.name)
                        except Exception:
                            pass
                        return data
                    
                    processed_files.append(file)
                
                html_file, models_file = processed_files
                
                # Get existing database values for matching
                existing_values = self._get_existing_database_values()
                
                # Create prompt
                prompt = self._create_extraction_prompt(brand, source_url, existing_values)
                
                # Generate content with file context
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content([
                    html_file,
                    models_file,
                    prompt
                ])
                
                # Parse response
                extracted_data = self._parse_gemini_response(response.text, data)
                
                # Clean up uploaded files
                try:
                    genai.delete_file(html_file.name)
                    genai.delete_file(models_file.name)
                except Exception:
                    pass  # Ignore cleanup errors
                
                return extracted_data
                
        except ImportError:
            data.add_error("google-generativeai package not installed")
            return data
        except Exception as e:
            data.add_error(f"Gemini parsing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return data
    
    def _get_models_structure(self) -> str:
        """Get the structure of relevant models for Gemini to understand the data format."""
        # Try to get BASE_DIR from settings first
        try:
            from django.conf import settings
            base_dir = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else None
        except Exception:
            base_dir = None
        
        # Read models.py file
        if base_dir:
            models_file = base_dir / 'toolanalysis' / 'models.py'
        else:
            models_file = Path(__file__).parent.parent.parent.parent / 'toolanalysis' / 'models.py'
        
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback: provide a simplified structure
            return """
# Django Models Structure for Product Data

class Products(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey('Brands')
    sku = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    # Many-to-many: itemtypes, categories, subcategories, batteryplatforms, batteryvoltages, features

class Components(models.Model):
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey('Brands')
    sku = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    motortype = models.ForeignKey('MotorTypes', blank=True, null=True)
    # Many-to-many: itemtypes, categories, subcategories, batteryplatforms, batteryvoltages, features, productlines

class Attributes(models.Model):
    name = models.TextField(unique=True)
    unit = models.TextField(blank=True, null=True)

class ComponentAttributes(models.Model):
    component = models.ForeignKey('Components')
    attribute = models.ForeignKey('Attributes')
    value = models.TextField(blank=True, null=True)

class Features(models.Model):
    name = models.TextField(unique=True)
    description = models.TextField(blank=True, null=True)

class ComponentFeatures(models.Model):
    component = models.ForeignKey('Components')
    feature = models.ForeignKey('Features')
    value = models.TextField(blank=True, null=True)

class Categories(models.Model):
    name = models.TextField()
    fullname = models.TextField(unique=True)

class ItemTypes(models.Model):
    name = models.TextField()
    fullname = models.TextField(unique=True)

class MotorTypes(models.Model):
    name = models.TextField(unique=True)

class BatteryVoltages(models.Model):
    value = models.IntegerField(unique=True)

class BatteryPlatforms(models.Model):
    name = models.TextField(unique=True)
    brand = models.ForeignKey('Brands', blank=True, null=True)
"""
    
    def _get_existing_database_values(self) -> Dict:
        """Query database for all existing values that Gemini should match against."""
        return {
            'attributes': [
                {'name': attr.name, 'unit': attr.unit or ''}
                for attr in Attributes.objects.all().order_by('name')
            ],
            'features': [
                {'name': feat.name, 'description': feat.description or ''}
                for feat in Features.objects.all().order_by('name')
            ],
            'itemtypes': [
                {'name': it.name, 'fullname': it.fullname}
                for it in ItemTypes.objects.all().order_by('name')
            ],
            'categories': [
                {'name': cat.name, 'fullname': cat.fullname}
                for cat in Categories.objects.all().order_by('name')
            ],
            'subcategories': [
                {'name': sub.name, 'fullname': sub.fullname}
                for sub in Subcategories.objects.all().order_by('name')
            ],
        }
    
    def _create_extraction_prompt(self, brand: str, source_url: str, existing_values: Dict) -> str:
        """Create the prompt for Gemini to extract product data."""
        # Format existing values for prompt
        attributes_str = '\n'.join([f"- {a['name']}" + (f" (unit: {a['unit']})" if a['unit'] else "") for a in existing_values['attributes'][:100]])
        features_str = '\n'.join([f"- {f['name']}" for f in existing_values['features'][:100]])
        itemtypes_str = '\n'.join([f"- {it['name']}" for it in existing_values['itemtypes'][:50]])
        categories_str = '\n'.join([f"- {c['name']}" for c in existing_values['categories'][:50]])
        subcategories_str = '\n'.join([f"- {s['name']}" for s in existing_values['subcategories'][:50]])
        
        return f"""Analyze the provided HTML product page and extract all product information needed to create entries in the database.

You have been provided with:
1. The complete HTML source code of a {brand} product page
2. The database models structure showing what fields and relationships exist

EXISTING DATABASE VALUES - YOU MUST MATCH TO THESE WHEN POSSIBLE:

Existing Attributes (for ComponentAttributes):
{attributes_str}
(Note: If an attribute has a unit, you may need to convert values. Return the normalized value in the attribute's unit format.)

Existing Features (for ComponentFeatures):
{features_str}

Existing ItemTypes:
{itemtypes_str}

Existing Categories:
{categories_str}

Existing Subcategories:
{subcategories_str}

Extract ALL available information and return it as a JSON object with this exact structure:

{{
  "product_name": "Full product name (required)",
  "sku": "Product SKU/model number (required)",
  "description": "Complete product description text",
  "image_url": "Main product image URL (full URL if relative)",
  "specifications": {{
    "Spec Key 1": "Spec Value 1",
    "Spec Key 2": "Spec Value 2",
    ...
  }},
  "product_specifications": [
    {{"name": "Spec Name 1", "value": "Spec Value 1"}},
    {{"name": "Spec Name 2", "value": "Spec Value 2"}},
    ...
  ],
  "component_attributes": [
    {{
      "attribute_name": "MATCHED_EXISTING_ATTRIBUTE_NAME or WARNING: No good match found",
      "value": "Converted/normalized value (in attribute's unit if specified)",
      "warning": "Optional warning if no good match exists"
    }},
    ...
  ],
  "features": [
    "Feature bullet point 1",
    "Feature bullet point 2",
    ...
  ],
  "component_features": [
    {{
      "feature_name": "MATCHED_EXISTING_FEATURE_NAME or WARNING: No good match found",
      "value": "Full feature description text",
      "warning": "Optional warning if no good match exists"
    }},
    ...
  ],
  "included_items": [
    "Item name 1",
    "Item name 2",
    ...
  ],
  "categories": [
    {{"name": "MATCHED_EXISTING_CATEGORY_NAME or WARNING: No good match", "warning": "Optional"}},
    ...
  ],
  "subcategories": [
    {{"name": "MATCHED_EXISTING_SUBCATEGORY_NAME or WARNING: No good match", "warning": "Optional"}},
    ...
  ],
  "itemtypes": [
    {{"name": "MATCHED_EXISTING_ITEMTYPE_NAME or WARNING: No good match", "warning": "Optional"}},
    ...
  ]
}}

EXTRACTION AND MAPPING GUIDELINES:
- Extract product_name from H1 tag, title tag, or main product heading
- Extract SKU from URL patterns (/product/SKU/), meta tags (product:retailer_item_id, sku, itemprop:sku), or data attributes
- Extract description from meta description, product description sections, or overview paragraphs (concatenate multiple paragraphs)
- Extract image_url from main product image (img src, data-src, data-lazy-src, or og:image meta tag) - ensure it's a complete URL
- For specifications: Extract raw key-value pairs into "specifications" AND also create "product_specifications" array for ProductSpecifications table
- For component_attributes: Match each specification to an existing Attribute. If unit conversion needed, convert. If no good match, use "WARNING: No good match found" as attribute_name and include warning
- For features: Extract raw feature text into "features" array
- For component_features: Match each feature to an existing Feature name. Use the matched Feature name and put full text in "value". If no good match, use "WARNING: No good match found" as feature_name
- Extract included_items from "Includes", "Included Items", "What's in the Box" sections (just item names, not descriptions)
- For categories/itemtypes/subcategories: Match to existing entries when possible. If no good match, include warning

IMPORTANT:
- Return ONLY valid JSON, no markdown formatting, no code blocks
- Include ALL available information - be thorough
- For specifications, normalize keys when possible (e.g., "Max Power (MWO)" -> "Max Power")
- Ensure image_url is a complete absolute URL (add domain if relative)
- MATCH TO EXISTING VALUES WHEN POSSIBLE - only use warnings when truly no good match exists
- For unit conversions (e.g., inches to cm), convert the value appropriately
- Include source_url: "{source_url}" in the JSON if source_url is provided

Return the JSON object now:"""
    
    def _parse_gemini_response(self, response_text: str, default_data: ParsedProductData) -> ParsedProductData:
        """Parse Gemini's JSON response into ParsedProductData."""
        try:
            # Clean response text - remove markdown code blocks
            json_text = response_text.strip()
            if json_text.startswith('```'):
                # Remove code block markers
                lines = json_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                json_text = '\n'.join(lines)
            
            # Try to find JSON object
            if json_text.startswith('{'):
                end_idx = json_text.rfind('}')
                if end_idx > 0:
                    json_text = json_text[:end_idx + 1]
            
            # Parse JSON
            parsed_json = json.loads(json_text)
            
            # Map to ParsedProductData
            data = ParsedProductData(
                source_url=parsed_json.get('source_url', default_data.source_url),
                brand=default_data.brand,
                product_name=parsed_json.get('product_name', ''),
                sku=parsed_json.get('sku', ''),
                description=parsed_json.get('description', ''),
                image_url=parsed_json.get('image_url', ''),
                specifications=parsed_json.get('specifications', {}),
                features=parsed_json.get('features', []),
                included_items=parsed_json.get('included_items', []),
                categories=[],  # Will be set from mapped categories
            )
            
            # Store extended data for preview/import
            # Product specifications (for ProductSpecifications table)
            data._product_specifications = parsed_json.get('product_specifications', [])
            
            # Component attributes (with matched attribute names)
            data._component_attributes = parsed_json.get('component_attributes', [])
            
            # Component features (with matched feature names)
            data._component_features = parsed_json.get('component_features', [])
            
            # Mapped categories/itemtypes/subcategories
            categories_list = parsed_json.get('categories', [])
            if isinstance(categories_list, list):
                data.categories = [
                    item['name'] if isinstance(item, dict) else str(item)
                    for item in categories_list
                ]
                data._category_mappings = [
                    item if isinstance(item, dict) else {'name': str(item), 'warning': ''}
                    for item in categories_list
                ]
            else:
                data.categories = []
                data._category_mappings = []
            
            data._subcategory_mappings = parsed_json.get('subcategories', [])
            data._itemtype_mappings = parsed_json.get('itemtypes', [])
            
            return data
            
        except json.JSONDecodeError as e:
            default_data.add_error(f"Failed to parse Gemini JSON response: {str(e)}")
            default_data.add_error(f"Response text: {response_text[:500]}")
            return default_data
        except Exception as e:
            default_data.add_error(f"Error processing Gemini response: {str(e)}")
            return default_data

