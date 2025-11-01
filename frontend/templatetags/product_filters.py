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
def make_list(value):
    """Create a list of integers from 0 to value-1 for looping"""
    try:
        count = int(value)
        return list(range(count))
    except (ValueError, TypeError):
        return []

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

@register.filter
def get_text_color_for_bg(bg_color):
    """
    Determine if text should be white or black based on background color brightness.
    Returns 'white' or 'black' based on luminance.
    """
    if not bg_color:
        return 'black'
    
    # Remove # if present
    bg_color = bg_color.strip().lstrip('#')
    
    # Convert hex to RGB
    try:
        if len(bg_color) == 6:
            r = int(bg_color[0:2], 16)
            g = int(bg_color[2:4], 16)
            b = int(bg_color[4:6], 16)
        elif len(bg_color) == 3:
            # Expand 3-digit hex to 6-digit (e.g., #F0A -> #FF00AA)
            r = int(bg_color[0] + bg_color[0], 16)
            g = int(bg_color[1] + bg_color[1], 16)
            b = int(bg_color[2] + bg_color[2], 16)
        else:
            return 'black'
        
        # Calculate relative luminance (perceived brightness)
        # Using WCAG luminance formula for better contrast
        def get_luminance(component):
            """Convert RGB component to linear luminance"""
            val = component / 255.0
            if val <= 0.03928:
                return val / 12.92
            else:
                return ((val + 0.055) / 1.055) ** 2.4
        
        r_lum = get_luminance(r)
        g_lum = get_luminance(g)
        b_lum = get_luminance(b)
        luminance = 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum
        
        # Use white text if background luminance is low, black if high
        # Threshold of 0.45 favors white text on vibrant colors (orange, red, etc.)
        # which typically look better with white text even if technically "bright"
        return 'white' if luminance < 0.45 else 'black'
    except (ValueError, IndexError):
        return 'black'

@register.filter
def componentclass_color(componentclass_name):
    """
    Return a color for a componentclass based on its name.
    Blue for Tools, Red for Batteries, Purple for Chargers, Green for Accessories.
    """
    if not componentclass_name:
        return '#0089D9'  # Default blue (site theme)
    
    componentclass_lower = componentclass_name.lower()
    
    # Special case: "Batteries & Chargers" group should use battery color (red) since batteries come first
    if componentclass_lower == 'batteries & chargers':
        return '#EF4444'  # Red for batteries (takes precedence)
    
    # Tools - site theme blue
    if 'tool' in componentclass_lower:
        return '#0089D9'
    
    # Batteries - complementary red (check before chargers to handle combined groups)
    if 'batter' in componentclass_lower:
        return '#EF4444'
    
    # Chargers - complementary purple-red shade
    if 'charger' in componentclass_lower:
        return '#C026D3'  # Violet/magenta - purple with red undertones
    
    # Accessories - complementary green
    if 'accessor' in componentclass_lower:
        return '#10B981'
    
    # Default to blue for unknown classes
    return '#0089D9'

@register.filter
def hex_to_rgba(hex_color, alpha=0.8):
    """
    Convert hex color to rgba format.
    """
    if not hex_color or not hex_color.startswith('#'):
        return f'rgba(0, 137, 217, {alpha})'  # Default blue
    
    try:
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        return f'rgba({r}, {g}, {b}, {alpha})'
    except (ValueError, IndexError):
        return f'rgba(0, 137, 217, {alpha})'  # Default fallback