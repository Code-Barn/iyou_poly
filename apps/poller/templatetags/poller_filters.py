# Copyright (C) 2026 David Byers dba Byers Brands
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

from django import template

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
