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


@register.filter(name="slugify")
def slugify(value):
    """
    Convert a string to a URL-friendly slug.
    """
    if not value:
        return ""

    # Convert to lowercase
    slug = value.lower()

    # Remove special characters
    slug = "".join(c if c.isalnum() or c in ["-", "_"] else "_" for c in slug)

    # Remove consecutive underscores
    while "__" in slug:
        slug = slug.replace("__", "_")

    # Remove leading/trailing underscores
    slug = slug.strip("_")

    # If the result is empty, return a default
    if not slug:
        return "credential"

    return slug
