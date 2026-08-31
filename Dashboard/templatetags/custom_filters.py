from django import template
import re

register = template.Library()

@register.filter
def highlight(text, search_term):
    if search_term:
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        highlighted_text = pattern.sub(f'<span style="background-color: yellow;">{search_term}</span>', text)
        return highlighted_text
    return text

@register.filter

def to_alpha(value):
    """Convert a number to its corresponding uppercase alphabet character."""
    try:
        return chr(65 + value - 1)  # A is 65 in ASCII
    except (TypeError, ValueError):
        return value


@register.filter
def get_item(dictionary, key):
    """Looks up a dict value by key from a template (dict[key] isn't valid template syntax)."""
    if not dictionary:
        return None
    return dictionary.get(key)