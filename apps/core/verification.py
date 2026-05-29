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

import datetime
import hashlib
import json
import logging
from typing import Any, Tuple

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
    if n == 0:
        return b"\x00" * pad
    return b"\x00" * pad + n.to_bytes((n.bit_length() + 7) // 8, "big")


def _b58encode(value: bytes) -> str:
    """Encode bytes to a base58btc string."""
    if not value:
        return ""
    n = int.from_bytes(value, "big")
    pad = 0
    for b in value:
        if b == 0:
            pad += 1
        else:
            break
    result = []
    while n > 0:
        n, rem = divmod(n, _BASE58_BASE)
        result.append(_BASE58_ALPHABET[rem])
    return _BASE58_ALPHABET[0] * pad + "".join(reversed(result))


# ---------------------------------------------------------------------------
# DID key extraction
# ---------------------------------------------------------------------------

# Multicodec identifier for Ed25519 public key (single byte 0xed).
_ED25519_PUB_MULTICODEC = b"\xed"
_ED25519_KEY_LENGTH = 32

# Expected length after base58btc decoding of a did:key Ed25519 pubkey.
# The ``did_rust`` library uses a 2-byte multicodec prefix (0xed 0x01),
# while some implementations use a 1-byte prefix (0xed only).
_EXPECTED_RAW_LENGTH_1BYTE = 1 + _ED25519_KEY_LENGTH   # 33
_EXPECTED_RAW_LENGTH_2BYTE = 2 + _ED25519_KEY_LENGTH   # 34


def _pubkey_from_did(did: str) -> Ed25519PublicKey | None:
    """Parse ``did:key:z6M...`` and return an ``Ed25519PublicKey``.

    Strips the ``did:key:`` prefix and the ``z`` multibase marker,
    base58btc-decodes the remaining payload, validates the multicodec
    prefix (``\\xed`` or ``\\xed\\x01`` for Ed25519), and returns the
    32-byte public key.
    """
    if not did.startswith("did:key:"):
        logger.warning("Unsupported DID method: %s", did)
        return None

    encoded = did.removeprefix("did:key:")

    if not encoded.startswith("z"):
        logger.warning("Expected multibase-base58btc prefix 'z', got: %s", encoded[:1])
        return None

    raw = _b58decode(encoded[1:])

    if len(raw) == _EXPECTED_RAW_LENGTH_1BYTE and raw[:1] == _ED25519_PUB_MULTICODEC:
        pubkey_bytes = raw[1:]
    elif len(raw) == _EXPECTED_RAW_LENGTH_2BYTE and raw[:1] == _ED25519_PUB_MULTICODEC and raw[1:2] == b"\x01":
        pubkey_bytes = raw[2:]
    else:
        logger.warning(
            "Unrecognised multicodec prefix or length (len=%d, prefix=%s) for DID: %s",
            len(raw), raw[:2].hex(), did,
        )
        return None

    try:
        return Ed25519PublicKey.from_public_bytes(pubkey_bytes)
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

    # Hash the payload to produce the 32-byte event ID the client signs
    event_id_bytes = hashlib.sha256(canonical_payload).digest()

    try:
        public_key.verify(signature, event_id_bytes)
        return True
    except Exception as exc:
        logger.debug("Ed25519 signature verification failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Attestation (Verifiable Credential) verification
# ---------------------------------------------------------------------------

# TODO: Sync with did_rust implementation (iyou_home/libs/did_rust).
#       The Rust implementation is the gold standard for VC verification.


def _is_issuer_trusted(issuer_did: str, credential_type: str) -> bool:
    """Check whether *issuer_did* is authorised to issue *credential_type*.

    Resolution order
    -----------------
    1. If ``settings.REQUIRE_TRUSTED_ISSUERS`` is ``True``, the issuer
       must appear in ``settings.TRUSTED_ISSUERS``.
    2. Otherwise the ``IssuerAuthorization`` table is consulted.
    3. If neither mechanism has data, the open-trust model is used
       (any issuer is accepted).
    """
    from django.conf import settings

    if getattr(settings, "REQUIRE_TRUSTED_ISSUERS", False):
        trusted = getattr(settings, "TRUSTED_ISSUERS", [])
        return issuer_did in trusted

    try:
        from apps.core.models import CredentialType, IssuerAuthorization

        ct = CredentialType.objects.filter(name=credential_type).first()
        if ct is None:
            # No credential type configured → no formal authorisation exists.
            # Fall back to open trust.
            return True
        return IssuerAuthorization.objects.filter(
            issuer_did=issuer_did,
            credential_type=ct,
            is_active=True,
        ).exists()
    except Exception:
        return True


def verify_attestation(
    attestation: dict[str, Any],
    required_type: str,
    voter_did: str,
    required_fidelity: int = 1,
) -> Tuple[bool, int]:
    """Cryptographically verify a W3C Verifiable Credential attestation.

    This is a pure-Python port of ``did_rust::internal_verify_vc``.  It
    performs the following checks in order:

    1. Structural integrity — ``proof``, ``issuer``, ``credentialSubject``
       must be present.
    2. Type matching — the attestation's ``type`` field must equal
       *required_type*.
    3. Subject binding — ``credentialSubject.id`` must equal *voter_did*.
    4. Freshness — ``expirationDate`` (if present) must not be in the
       past.
    5. Issuer trust — the issuer must be authorised for this credential
       type (see :func:`_is_issuer_trusted`).
    6. Cryptographic signature — the Ed25519 signature in ``proof`` is
       verified against the canonical JSON payload using the issuer's
       public key, extracted from their ``did:key:`` identifier.

    Parameters
    ----------
    attestation:
        The full Verifiable Credential object (JSON dict with ``proof``).
    required_type:
        The credential ``type`` that the poll requires.
    voter_did:
        The voter's DID — must match ``credentialSubject.id``.
    required_fidelity:
        Minimum trust fidelity level required (1=Social/Peer,
        2=Institutional, 3=Hardware/Security).  Defaults to 1.

    Returns
    -------
    ``(True, fidelity_score)`` if every check passes;
    ``(False, fidelity_score)`` otherwise.
    """
    # --- 1. Structural integrity ---
    proof = attestation.get("proof")
    if not proof or not isinstance(proof, dict):
        logger.warning("Attestation missing or invalid proof block")
        return False, 0

    issuer_did = attestation.get("issuer")
    if not issuer_did or not isinstance(issuer_did, str):
        logger.warning("Attestation missing or invalid issuer DID")
        return False, 0

    credential_subject = attestation.get("credentialSubject")
    if not credential_subject or not isinstance(credential_subject, dict):
        logger.warning("Attestation missing or invalid credentialSubject")
        return False, 0

    # --- 2. Type matching ---
    cred_type = attestation.get("type", "")
    if isinstance(cred_type, list):
        cred_type = cred_type[0] if cred_type else ""
    if cred_type != required_type:
        logger.warning(
            "Attestation type mismatch: got '%s', expected '%s'",
            cred_type, required_type,
        )
        return False, 0

    # --- 3. Subject binding ---
    if credential_subject.get("id") != voter_did:
        logger.warning(
            "Attestation subject id '%s' does not match voter_did '%s'",
            credential_subject.get("id"), voter_did,
        )
        return False, 0

    # --- 4. Freshness ---
    exp_str = attestation.get("expirationDate")
    if exp_str:
        try:
            exp_str_iso = exp_str.replace("Z", "+00:00")
            exp_time = datetime.datetime.fromisoformat(exp_str_iso)
            if datetime.datetime.now(datetime.timezone.utc) > exp_time:
                logger.warning("Attestation expired at %s", exp_str)
                return False, 0
        except (ValueError, TypeError):
            logger.warning("Unparseable expirationDate '%s'", exp_str)
            return False, 0

    # --- 5. Issuer trust ---
    if not _is_issuer_trusted(issuer_did, required_type):
        logger.warning(
            "Issuer '%s' is not trusted for credential type '%s'",
            issuer_did, required_type,
        )
        return False, 0

    # --- 6. Cryptographic signature ---
    sig_b58 = proof.get("signatureValue")
    if not sig_b58 or not isinstance(sig_b58, str):
        logger.warning("Attestation proof missing signatureValue")
        return False, 0

    public_key = _pubkey_from_did(issuer_did)
    if public_key is None:
        logger.warning("Could not extract public key from issuer DID '%s'", issuer_did)
        return False, 0

    # The canonical payload is the attestation *minus* the proof block,
    # serialised preserving insertion order so that the digest matches
    # what ``serde_json`` (used in ``did_rust``) produces.
    payload = {k: v for k, v in attestation.items() if k != "proof"}
    canonical_payload = json.dumps(
        payload,
        sort_keys=False,  # preserve insertion order (matches serde_json)
        separators=(",", ":"),
    ).encode("utf-8")

    try:
        sig_bytes = _b58decode(sig_b58)
        public_key.verify(sig_bytes, canonical_payload)
    except Exception as exc:
        logger.debug("Attestation Ed25519 signature verification failed: %s", exc)
        return False, 0

    # --- 7. Fidelity check ---
    fidelity_score = attestation.get("fidelity_score", 1)
    if not isinstance(fidelity_score, int) or fidelity_score < 1 or fidelity_score > 3:
        fidelity_score = 1
    if fidelity_score < required_fidelity:
        logger.warning(
            "Attestation fidelity %d < required fidelity %d",
            fidelity_score, required_fidelity,
        )
        return False, fidelity_score

    return True, fidelity_score


def verify_credential_presentation(
    vp_json: dict[str, Any],
    required_type: str,
    challenge: str,
    required_fidelity: int = 1,
) -> Tuple[bool, int, dict[str, Any] | None]:
    """Verify a W3C Verifiable Presentation wrapping a credential attestation.

    Performs a dual-layer cryptographic check:

    **VP layer** — signed by the *holder* (voter). Proves the presenter
    controls the DID they claim.

    **VC layer** — the inner Verifiable Credential, verified via
    :func:`verify_attestation`. Proves the credential was issued by a
    trusted issuer.

    Parameters
    ----------
    vp_json:
        The full Verifiable Presentation object (JSON dict with
        ``proof``, ``verifiableCredential``, ``holder``).
    required_type:
        The credential ``type`` that the poll requires.
    challenge:
        The server-generated nonce that must match ``proof.challenge``.
    required_fidelity:
        Minimum trust fidelity level (passed through to
        :func:`verify_attestation`).

    Returns
    -------
    ``(True, fidelity_score, inner_vc)`` if both VP and VC layers pass;
    ``(False, 0, None)`` otherwise.
    """
    # --- 1. VP structural integrity ---
    vp_type = vp_json.get("type", [])
    if isinstance(vp_type, str):
        vp_type = [vp_type]
    if "VerifiablePresentation" not in vp_type:
        logger.warning("VP missing VerifiablePresentation type")
        return False, 0, None

    vc_list = vp_json.get("verifiableCredential")
    if not isinstance(vc_list, list) or not vc_list:
        logger.warning("VP missing or empty verifiableCredential array")
        return False, 0, None

    proof = vp_json.get("proof")
    if not proof or not isinstance(proof, dict):
        logger.warning("VP missing or invalid proof block")
        return False, 0, None

    holder_did = vp_json.get("holder")
    if not holder_did or not isinstance(holder_did, str):
        logger.warning("VP missing or invalid holder DID")
        return False, 0, None

    # --- 2. Challenge binding ---
    if proof.get("challenge") != challenge:
        logger.warning(
            "VP challenge mismatch: got '%s', expected '%s'",
            proof.get("challenge"), challenge,
        )
        return False, 0, None

    # --- 3. VC layer — delegate to verify_attestation ---
    inner_vc = vc_list[0]
    is_valid, fidelity_score = verify_attestation(
        inner_vc, required_type, holder_did,
        required_fidelity=required_fidelity,
    )
    if not is_valid:
        return False, 0, None

    # --- 4. VP envelope Ed25519 verification ---
    sig_b58 = proof.get("signatureValue")
    if not sig_b58 or not isinstance(sig_b58, str):
        logger.warning("VP proof missing signatureValue")
        return False, 0, None

    holder_pubkey = _pubkey_from_did(holder_did)
    if holder_pubkey is None:
        logger.warning("Could not extract public key from holder DID '%s'", holder_did)
        return False, 0, None

    # Canonical payload: VP *minus* the proof block, serialised with
    # ``sort_keys=True`` for deterministic signing across Rust/Python.
    vp_without_proof = {k: v for k, v in vp_json.items() if k != "proof"}
    canonical_payload = json.dumps(
        vp_without_proof,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    try:
        sig_bytes = _b58decode(sig_b58)
        holder_pubkey.verify(sig_bytes, canonical_payload)
    except Exception as exc:
        logger.debug("VP Ed25519 signature verification failed: %s", exc)
        return False, 0, None

    return True, fidelity_score, inner_vc


def verify_revocation(voter_did: str, issuer_did: str) -> bool:
    """Check whether *issuer_did* has revoked a credential for *voter_did*.

    Scans the local ledger (``RevocationAttestation`` table) for an active
    revocation matching both DIDs.  Returns ``True`` if a revocation exists
    (i.e. the credential **is** revoked).

    If no matching record is found, the credential is assumed valid, so
    this function returns ``False``.
    """
    try:
        from apps.poller.models import RevocationAttestation

        return RevocationAttestation.objects.filter(
            issuer_did=issuer_did,
            subject_did=voter_did,
        ).exists()
    except Exception:
        return False
