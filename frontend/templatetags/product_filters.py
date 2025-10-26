from django import template

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
