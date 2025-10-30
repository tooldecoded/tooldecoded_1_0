from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

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
