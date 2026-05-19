# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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
