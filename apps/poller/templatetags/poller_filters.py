from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
def percentage(value, total):
    """
    Calculate percentage of value relative to total.
    Returns 0 if total is 0 to avoid division by zero.
    """
    try:
        value = int(value)
        total = int(total)
        if total == 0:
            return 0
        return int((value * 100) / total)
    except (ValueError, TypeError):
        return 0
