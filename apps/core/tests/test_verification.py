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

"""Tests for attestation (Verifiable Credential) verification."""

import copy
import datetime
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.verification import (
    _b58encode,
    _b58decode,
    _pubkey_from_did,
    verify_attestation,
    verify_vote_signature,
)


def _did_from_pubkey(pubkey_bytes: bytes) -> str:
    """Build a ``did:key:z6M...`` identifier from raw Ed25519 public key bytes."""
    multicodec = b"\xed\x01" + pubkey_bytes
    return f"did:key:z{_b58encode(multicodec)}"


def _sign_vc_payload(payload: dict, private_key: Ed25519PrivateKey) -> str:
    """Sign a VC payload (without proof) and return a base58btc-encoded signature.

    The serialisation matches ``serde_json`` (insertion-order, no extra
    whitespace) so that ``verify_attestation`` can verify the result.
    """
    canonical = json.dumps(payload, sort_keys=False, separators=(",", ":")).encode("utf-8")
    sig_bytes = private_key.sign(canonical)
    return _b58encode(sig_bytes)


def _build_signed_vc(
    *,
    credential_type: str = "ProofOfResidency",
    issuer_did: str = "",
    subject_did: str = "did:key:zSubject123",
    expiration_date: str | None = "2099-12-31T23:59:59Z",
    fidelity_score: int | None = None,
    private_key: Ed25519PrivateKey | None = None,
    tamper_field: str | None = None,
) -> dict:
    """Build a signed W3C Verifiable Credential for testing.

    Parameters
    ----------
    credential_type:
        The ``type`` of the credential (string — the test helper wraps it
        in an array automatically to match W3C conventions).
    issuer_did:
        DID of the issuer.  If empty, a fresh keypair is generated.
    subject_did:
        DID of the credential subject (the voter).
    expiration_date:
        ISO-8601 expiration or ``None`` to omit the field.
    fidelity_score:
        Optional trust fidelity level (1-3).  Omitted when ``None``.
    private_key:
        Optional pre-existing private key.  If ``None``, a new one is
        generated (and *issuer_did* is derived from it).
    tamper_field:
        If set, the named field's value is replaced with ``"TAMPERED"``
        *after* signing, simulating a forgery.
    """
    if private_key is None:
        private_key = Ed25519PrivateKey.generate()
    if not issuer_did:
        issuer_did = _did_from_pubkey(
            private_key.public_key().public_bytes_raw()
        )

    vc_body = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": [credential_type],
        "issuer": issuer_did,
        "issuanceDate": "2026-01-01T00:00:00Z",
        "credentialSubject": {
            "id": subject_did,
        },
    }
    if expiration_date is not None:
        vc_body["expirationDate"] = expiration_date
    if fidelity_score is not None:
        vc_body["fidelity_score"] = fidelity_score

    sig_b58 = _sign_vc_payload(vc_body, private_key)

    vc = copy.deepcopy(vc_body)
    vc["proof"] = {
        "type": "Ed25519Signature2018",
        "verificationMethod": f"{issuer_did}#keys-1",
        "signatureValue": sig_b58,
    }

    if tamper_field:
        parts = tamper_field.split(".", 1)
        if len(parts) == 1:
            vc[parts[0]] = "TAMPERED"
        else:
            vc[parts[0]][parts[1]] = "TAMPERED"

    return vc


class VerifyAttestationTests(TestCase):
    """``verify_attestation(…)`` — full coverage."""

    # Use open-trust model so we don't need DB setup for issuer auth.
    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_accepts_valid_attestation(self):
        """A correctly signed, non-expired attestation must pass."""
        vc = _build_signed_vc()
        valid, fidelity = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_type_mismatch(self):
        """Wrong credential type → ``False``."""
        vc = _build_signed_vc()
        valid, _ = verify_attestation(vc, "MunicipalVoter", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_wrong_subject(self):
        """``credentialSubject.id`` differs from *voter_did* → ``False``."""
        vc = _build_signed_vc()
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zWrongVoter")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_expired_attestation(self):
        """Past ``expirationDate`` → ``False``."""
        vc = _build_signed_vc(expiration_date="2020-01-01T00:00:00Z")
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_accepts_missing_expiration(self):
        """No ``expirationDate`` is acceptable."""
        vc = _build_signed_vc(expiration_date=None)
        valid, fidelity = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_tampered_issuer(self):
        """Forged ``issuer`` field → signature mismatch → ``False``."""
        vc = _build_signed_vc(tamper_field="issuer")
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_tampered_subject_id(self):
        """Forged ``credentialSubject.id`` → signature mismatch → ``False``."""
        vc = _build_signed_vc(tamper_field="credentialSubject.id")
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_missing_proof(self):
        """No ``proof`` block → ``False``."""
        vc = _build_signed_vc()
        del vc["proof"]
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_missing_issuer(self):
        """No ``issuer`` field → ``False``."""
        vc = _build_signed_vc()
        del vc["issuer"]
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_missing_credential_subject(self):
        """No ``credentialSubject`` → ``False``."""
        vc = _build_signed_vc()
        del vc["credentialSubject"]
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_bad_signature_value(self):
        """Random base58 string as signature → ``False``."""
        vc = _build_signed_vc()
        vc["proof"]["signatureValue"] = "z6Mkfakefakefakefakefakefakefakefake"
        valid, _ = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertFalse(valid)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_preserves_key_order_for_signature(self):
        """Key insertion order from source JSON is preserved during
        serialisation (matching ``serde_json`` behaviour)."""
        vc = _build_signed_vc()
        valid, fidelity = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_type_as_string_not_list(self):
        """``type`` may be a plain string (not an array)."""
        private_key = Ed25519PrivateKey.generate()
        issuer_did = _did_from_pubkey(private_key.public_key().public_bytes_raw())
        vc_body = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": "ProofOfResidency",
            "issuer": issuer_did,
            "issuanceDate": "2026-01-01T00:00:00Z",
            "credentialSubject": {"id": "did:key:zSubject123"},
            "expirationDate": "2099-12-31T23:59:59Z",
        }
        sig_b58 = _sign_vc_payload(vc_body, private_key)
        vc = {**vc_body, "proof": {"signatureValue": sig_b58}}
        valid, fidelity = verify_attestation(vc, "ProofOfResidency", "did:key:zSubject123")
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    # --- Fidelity tests ---

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_fidelity_defaults_to_1(self):
        """Attestation without ``fidelity_score`` has an effective fidelity of 1."""
        vc = _build_signed_vc()
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=1,
        )
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_fidelity_1_meets_requirement_1(self):
        """Fidelity 1 attestation satisfies a poll requiring 1."""
        vc = _build_signed_vc(fidelity_score=1)
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=1,
        )
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_fidelity_2_satisfies_requirement_2(self):
        """Fidelity 2 attestation satisfies a poll requiring 2."""
        vc = _build_signed_vc(fidelity_score=2)
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=2,
        )
        self.assertTrue(valid)
        self.assertEqual(fidelity, 2)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_fidelity_3_satisfies_requirement_2(self):
        """Fidelity 3 attestation is accepted for a poll requiring 2
        (higher fidelity satisfies lower bars)."""
        vc = _build_signed_vc(fidelity_score=3)
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=2,
        )
        self.assertTrue(valid)
        self.assertEqual(fidelity, 3)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_rejects_insufficient_fidelity(self):
        """Fidelity 1 attestation is rejected when poll requires 2."""
        vc = _build_signed_vc(fidelity_score=1)
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=2,
        )
        self.assertFalse(valid)
        self.assertEqual(fidelity, 1)

    @override_settings(REQUIRE_TRUSTED_ISSUERS=False)
    def test_fidelity_out_of_range_clamped_to_1(self):
        """Out-of-range fidelity (e.g. 99) is clamped down to 1."""
        vc = _build_signed_vc(fidelity_score=99)
        valid, fidelity = verify_attestation(
            vc, "ProofOfResidency", "did:key:zSubject123",
            required_fidelity=1,
        )
        self.assertTrue(valid)
        self.assertEqual(fidelity, 1)


class B58RoundTripTests(TestCase):
    """``_b58encode`` / ``_b58decode`` round-trip consistency."""

    def test_round_trip_empty(self):
        self.assertEqual(_b58decode(_b58encode(b"")), b"")

    def test_round_trip_single_byte(self):
        for b in range(256):
            payload = bytes([b])
            self.assertEqual(_b58decode(_b58encode(payload)), payload)

    def test_round_trip_padding(self):
        payload = b"\x00\x00\x00hello"
        self.assertEqual(_b58decode(_b58encode(payload)), payload)

    def test_round_trip_signature_sized(self):
        payload = bytes(range(64))
        self.assertEqual(_b58decode(_b58encode(payload)), payload)
