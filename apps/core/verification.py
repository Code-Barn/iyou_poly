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

"""
Cryptographic verification for the iyou_poly v2 sovereign mesh.

Provides pure-Python Ed25519 signature validation using the standard
``cryptography`` library.  No external submodules, bridge connections,
or Rust bindings are required — DID public keys are extracted directly
from ``did:key:z6M...`` identifiers.
"""

import json
import logging
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base58BTC (Bitcoin-style) — lightweight inline implementation
# ---------------------------------------------------------------------------

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_BASE58_BASE = len(_BASE58_ALPHABET)
_B58_DECODE = {ch: i for i, ch in enumerate(_BASE58_ALPHABET)}


def _b58decode(value: str) -> bytes:
    """Decode a base58btc string to bytes."""
    if not value:
        return b""
    n = 0
    for ch in value:
        n = n * _BASE58_BASE + _B58_DECODE[ch]
    pad = 0
    for ch in value:
        if ch == _BASE58_ALPHABET[0]:
            pad += 1
        else:
            break
    return b"\x00" * pad + n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")


# ---------------------------------------------------------------------------
# DID key extraction
# ---------------------------------------------------------------------------

# Multicodec identifier for Ed25519 public key (single byte 0xed).
_ED25519_PUB_MULTICODEC = b"\xed"
_ED25519_KEY_LENGTH = 32

# Expected length after base58btc decoding of a did:key Ed25519 pubkey
_EXPECTED_RAW_LENGTH = len(_ED25519_PUB_MULTICODEC) + _ED25519_KEY_LENGTH  # 33


def _pubkey_from_did(did: str) -> Ed25519PublicKey | None:
    """Parse ``did:key:z6M...`` and return an ``Ed25519PublicKey``.

    Strips the ``did:key:`` prefix and the ``z`` multibase marker,
    base58btc-decodes the remaining payload, validates the multicodec
    prefix (``\\xed`` for Ed25519), and returns the 32-byte public key.
    """
    if not did.startswith("did:key:"):
        logger.warning("Unsupported DID method: %s", did)
        return None

    encoded = did.removeprefix("did:key:")

    if not encoded.startswith("z"):
        logger.warning("Expected multibase-base58btc prefix 'z', got: %s", encoded[:1])
        return None

    raw = _b58decode(encoded[1:])

    if len(raw) != _EXPECTED_RAW_LENGTH:
        logger.warning(
            "Unexpected decoded length %d (expected %d) for DID: %s",
            len(raw), _EXPECTED_RAW_LENGTH, did,
        )
        return None

    if raw[:1] != _ED25519_PUB_MULTICODEC:
        logger.warning(
            "Unexpected multicodec prefix %s (expected %s) for DID: %s",
            raw[:1].hex(), _ED25519_PUB_MULTICODEC.hex(), did,
        )
        return None

    try:
        return Ed25519PublicKey.from_public_bytes(raw[1:])
    except Exception as exc:
        logger.warning("Failed to load Ed25519 public key from DID %s: %s", did, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_vote_signature(
    voter_did: str,
    signature_hex: str,
    vote_envelope: dict[str, Any],
) -> bool:
    """Verify an Ed25519 signature on a canonically-serialised vote envelope.

    Parameters
    ----------
    voter_did:
        The voter's DID string (``did:key:z6M...``).
    signature_hex:
        Hex-encoded Ed25519 signature (128 hex chars).
    vote_envelope:
        Signed payload dict (e.g. ``{"poll_id": …, "option_id": …,
        "voter_did": …, "timestamp": …}``).

    Returns
    -------
    ``True`` when the signature is cryptographically valid for the
    canonical payload under the voter's public key; ``False`` otherwise.
    """
    if not voter_did or not signature_hex:
        return False

    public_key = _pubkey_from_did(voter_did)
    if public_key is None:
        return False

    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        logger.warning("Signature is not valid hex: %s", signature_hex[:32])
        return False

    # Canonical serialisation  --  guaranteed deterministic ordering
    canonical_payload = json.dumps(
        vote_envelope,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    try:
        public_key.verify(signature, canonical_payload)
        return True
    except Exception as exc:
        logger.debug("Ed25519 signature verification failed: %s", exc)
        return False
