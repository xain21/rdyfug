# custom_filters.py
from django import template

register = template.Library()

@register.filter
def to_alpha(value):
    """Convert a number to its corresponding uppercase alphabet character."""
    try:
        # Convert to uppercase letter starting from A (1 = A, 2 = B, etc.)
        return chr(64 + value)
    except (TypeError, ValueError):
        return value
