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
