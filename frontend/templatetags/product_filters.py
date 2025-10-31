from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

def format_attribute_value_helper(component_attr):
    """
    Format ComponentAttributes value based on the attribute's unit field.
    Returns ONLY the formatted numeric value (without unit).
    
    Formatting rules:
    - No decimals (whole numbers): MPH, CFM, PSI, W, °F, lm, dB, IPM, RPM, SPM, in-lb
    - One decimal: Ah, A, in
    - Float/as needed: degrees
    - Conditional (threshold 100): V - 0 decimals if >= 100, 1 decimal if < 100
    - Currency (2 decimals): USD, $
    - No commas anywhere
    """
    if not component_attr:
        return ""
    
    value = component_attr.value
    attribute = getattr(component_attr, 'attribute', None)
    
    # Early returns
    if value is None or value == "":
        return value or ""
    
    if not attribute:
        return value
    
    unit = getattr(attribute, 'unit', None)
    if not unit:
        return value
    
    unit = str(unit).strip().lower()
    
    try:
        # Convert value to float for formatting
        clean_value = str(value).replace(',', '').replace(' ', '').strip()
        numeric_value = float(clean_value)
        
        # Currency - 2 decimals, no commas, include $ prefix
        if unit in ['$', 'usd', 'dollars', 'dollar']:
            return f"${numeric_value:.2f}"
        
        # Voltage - conditional decimals (threshold 100)
        if unit in ['v', 'volt', 'volts', 'voltage']:
            decimals = 0 if abs(numeric_value) >= 100 else 1
            return f"{numeric_value:.{decimals}f}"
        
        # No decimals (whole numbers)
        if unit in ['mph', 'cfm', 'psi', 'w', 'watts', 'watt', 
                   '°f', 'f', 'fahrenheit',
                   'lm', 'lumen', 'lumens',
                   'db', 'decibel', 'decibels',
                   'ipm', 'rpm', 'spm',
                   'in-lb', 'in-lbs', 'inch-pound', 'inch-pounds']:
            return f"{int(numeric_value)}"
        
        # One decimal
        if unit in ['ah', 'amp-hour', 'amp-hours', 'ampere-hour', 'ampere-hours',
                   'a', 'amp', 'amps', 'ampere', 'amperes', 'amperage',
                   'in', 'inch', 'inches']:
            return f"{numeric_value:.1f}"
        
        # Float/as needed - degrees (display as-is, preserve original decimals)
        if unit in ['degrees', 'degree', 'deg', '°']:
            # If value has decimals, preserve them; otherwise format nicely
            if '.' in str(value):
                return f"{numeric_value}"
            else:
                return f"{int(numeric_value)}"
        
        # Default: If unit exists but no rule matches, return with 1 decimal
        return f"{numeric_value:.1f}"
    
    except (ValueError, TypeError):
        # Can't convert to number - return original value
        return value
    except Exception:
        # Any other error - return original value
        return value

@register.filter
def split_bullets(value):
    """Split bullets text by newlines and return a list of non-empty lines"""
    if not value:
        return []
    lines = value.split('\n')
    return [line.strip() for line in lines if line.strip()]

@register.filter
def lookup(dictionary, key):
    """Look up a key in a dictionary"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None

@register.filter
def usd(value):
    """Format a numeric value as USD ($1,234.56); return '—' if None/blank"""
    if value is None or value == "":
        return "—"
    try:
        # Coerce to Decimal for stable money formatting
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
        return f"${amount:,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return "—"

@register.filter
def format_attribute_value(component_attr):
    """
    Template filter to format ComponentAttributes value based on Attributes.displayformat.
    Accepts a ComponentAttributes instance.
    If displayformat is not set or formatting fails, returns original value.
    """
    return format_attribute_value_helper(component_attr)

@register.filter
def get_component_attr_for_attribute(component_attributes, attribute):
    """
    Get the ComponentAttribute that matches the given attribute from a queryset.
    Returns the ComponentAttribute instance or None if not found.
    """
    if not component_attributes or not attribute:
        return None
    try:
        for comp_attr in component_attributes:
            if hasattr(comp_attr, 'attribute') and comp_attr.attribute.id == attribute.id:
                return comp_attr
    except Exception:
        pass
    return None