"""Gemini AI helper for enhancing manufacturer data parsing and normalization."""

import json
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache


class GeminiDataEnhancer:
    """Strategic LLM assistance for data normalization and inference (optional, fails gracefully)."""
    
    def __init__(self):
        self.enabled = getattr(settings, 'USE_GEMINI_ENHANCEMENT', False)
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    def _call_gemini(self, prompt: str, cache_key: Optional[str] = None) -> Optional[str]:
        """Call Gemini API with caching. Returns None if unavailable."""
        if not self.enabled or not self.api_key:
            return None
        
        # Check cache first
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Cache result
            if cache_key and text:
                cache.set(cache_key, text, 3600)  # Cache for 1 hour
            
            return text
        except ImportError:
            # google.generativeai not installed
            pass
        except Exception:
            # Silently fail - this is optional enhancement
            pass
        
        return None
    
    def normalize_attribute_name(self, spec_key: str, spec_value: str, context: Dict[str, Any] = None) -> str:
        """
        Use Gemini to map manufacturer-specific terms to standard attribute names.
        
        Args:
            spec_key: Raw specification key from manufacturer page
            spec_value: Specification value
            context: Additional context (product name, brand, etc.)
            
        Returns:
            Normalized attribute name or original if unavailable
        """
        if not self.enabled:
            return spec_key
        
        cache_key = f"gemini_attr_norm:{spec_key.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        prompt = f"""Map this manufacturer specification key to a standard attribute name for power tools/components.

Original key: "{spec_key}"
Value: "{spec_value}"

Return ONLY the normalized attribute name, nothing else. Examples:
- "MWO" -> "Max Power"
- "No Load Speed [RPM]" -> "Speed"
- "Chuck Size [in]" -> "Chuck Size"
- "Is Brushless?" -> "Brushless"

Normalized name:"""
        
        result = self._call_gemini(prompt, cache_key)
        if result:
            normalized = result.strip().strip('"').strip("'")
            if normalized and len(normalized) < 100:
                cache.set(cache_key, normalized, 86400)  # Cache for 24 hours
                return normalized
        
        return spec_key
    
    def extract_structured_features(self, feature_texts: List[str]) -> List[Dict[str, str]]:
        """
        Parse unstructured bullet points into structured feature name/value pairs.
        
        Args:
            feature_texts: List of feature bullet point strings
            
        Returns:
            List of dicts with 'name' and 'value' keys
        """
        if not self.enabled or not feature_texts:
            return []
        
        prompt = f"""Parse these product feature bullet points into structured name-value pairs.

Features:
{json.dumps(feature_texts, indent=2)}

Return a JSON array where each item has "name" (short feature name) and "value" (full description).
Example format:
[
  {{"name": "Versatile Capabilities", "value": "Take on a variety of applications..."}},
  {{"name": "Reach Tough Areas", "value": "Access hard-to-reach spaces..."}}
]

Return ONLY valid JSON, nothing else:"""
        
        result = self._call_gemini(prompt, f"gemini_features:{hash(tuple(feature_texts))}")
        if result:
            try:
                # Try to extract JSON from response
                json_str = result.strip()
                if json_str.startswith('```'):
                    json_str = json_str.split('```')[1]
                    if json_str.startswith('json'):
                        json_str = json_str[4:]
                json_str = json_str.strip()
                
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        
        # Fallback: simple structure
        return [{"name": text[:50], "value": text} for text in feature_texts[:10]]
    
    def infer_missing_fields(self, parsed_data, existing_attributes: List[str] = None) -> Dict[str, Any]:
        """
        Infer missing critical fields from available context.
        
        Args:
            parsed_data: ParsedProductData object
            existing_attributes: List of existing attribute names for reference
            
        Returns:
            Dict of inferred field values
        """
        if not self.enabled:
            return {}
        
        missing = []
        context_parts = []
        
        if not parsed_data.sku and parsed_data.product_name:
            missing.append("SKU")
            context_parts.append(f"Product name: {parsed_data.product_name}")
        
        if missing:
            prompt = f"""From this product information, infer missing critical fields.

Product Name: {parsed_data.product_name}
Brand: {parsed_data.brand}
Description: {parsed_data.description[:200]}
Specifications: {json.dumps(dict(list(parsed_data.specifications.items())[:5]), indent=2)}

Missing fields to infer: {', '.join(missing)}

Return a JSON object with the inferred values. Example:
{{"sku": "DCD803B", "voltage": "20"}}

Return ONLY valid JSON, nothing else:"""
            
            result = self._call_gemini(prompt, f"gemini_infer:{hash(parsed_data.product_name)}")
            if result:
                try:
                    json_str = result.strip()
                    if json_str.startswith('```'):
                        json_str = json_str.split('```')[1]
                        if json_str.startswith('json'):
                            json_str = json_str[4:]
                    json_str = json_str.strip()
                    
                    return json.loads(json_str)
                except Exception:
                    pass
        
        return {}
    
    def map_categories(self, product_name: str, description: str, specs: Dict[str, str]) -> List[str]:
        """
        Intelligently map product to appropriate Categories and ItemTypes.
        
        Args:
            product_name: Product name
            description: Product description
            specs: Specifications dict
            
        Returns:
            List of suggested category names
        """
        if not self.enabled:
            return []
        
        prompt = f"""From this product information, suggest appropriate categories for a power tool database.

Product: {product_name}
Description: {description[:300]}
Key specs: {json.dumps(dict(list(specs.items())[:5]), indent=2)}

Suggest 3-5 category names that would fit this product. Consider:
- Tool type (drill, saw, etc.)
- Power source (cordless, corded)
- Brand line (if applicable)

Return a JSON array of category names. Example:
["Drills", "Drill Drivers", "Cordless Tools", "20V MAX"]

Return ONLY valid JSON array, nothing else:"""
        
        result = self._call_gemini(prompt, f"gemini_cats:{hash(product_name)}")
        if result:
            try:
                json_str = result.strip()
                if json_str.startswith('```'):
                    json_str = json_str.split('```')[1]
                    if json_str.startswith('json'):
                        json_str = json_str[4:]
                json_str = json_str.strip()
                
                categories = json.loads(json_str)
                if isinstance(categories, list):
                    return [str(c) for c in categories[:5]]
            except Exception:
                pass
        
        return []
    
    def enhance_description(self, raw_description: str) -> str:
        """Clean and format product descriptions."""
        if not self.enabled or not raw_description:
            return raw_description
        
        # Simple enhancement - can be improved with Gemini if needed
        # For now, just clean up whitespace
        cleaned = ' '.join(raw_description.split())
        return cleaned[:1000]  # Limit length

