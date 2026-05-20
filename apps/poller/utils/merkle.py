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

import hashlib

def calculate_merkle_root(items):
    """
    Calculate the Merkle root of a list of items using SHA-256.
    """
    if not items:
        return None

    # Start with the hashes of the items
    hashes = [hashlib.sha256(str(item).encode()).hexdigest() for item in items]

    while len(hashes) > 1:
        # If odd number of hashes, duplicate the last one
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])

        new_hashes = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i+1]
            new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
        hashes = new_hashes

    return hashes[0]
