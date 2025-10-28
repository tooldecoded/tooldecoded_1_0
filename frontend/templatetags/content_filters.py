import markdown
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def markdownify(text):
    """
    Convert markdown text to HTML and sanitize it for safe display.
    """
    if not text:
        return ""
    
    # Convert markdown to HTML using safe, built-in extensions
    html = markdown.markdown(text, extensions=['markdown.extensions.tables', 'markdown.extensions.fenced_code'])
    
    # Define allowed HTML tags and attributes for security
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    
    allowed_attributes = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'table': ['class'],
        'th': ['scope'],
        'td': ['colspan', 'rowspan']
    }
    
    # Sanitize the HTML
    clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes)
    
    return mark_safe(clean_html)

@register.filter
def split(value, delimiter):
    """
    Split a string by delimiter and return a list.
    """
    if not value:
        return []
    return value.split(delimiter)