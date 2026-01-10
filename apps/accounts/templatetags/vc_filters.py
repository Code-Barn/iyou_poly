"""
Custom template filters for VC formatting.
"""

import json

from django import template

register = template.Library()


@register.filter(name="to_json_compact")
def to_json_compact(value):
    """
    Convert a Python object to compact JSON string.
    """
    if value is None:
        return ""
    return json.dumps(value, separators=(",", ":"))


@register.filter(name="to_json_pretty")
def to_json_pretty(value):
    """
    Convert a Python object to pretty-printed JSON string.
    """
    if value is None:
        return ""
    return json.dumps(value, indent=2)
