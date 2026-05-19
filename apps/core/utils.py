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
Utility functions for the core app.

This module provides utilities for conflict resolution, trust scoring, and other federation-related functions.
"""

import hashlib
import datetime
import math
from typing import Optional


class ConflictResolution:
    """
    Handles conflicts when nodes have divergent data.
    Uses last-write-wins with version vectors.
    """

    @staticmethod
    def resolve(data_a: dict, data_b: dict) -> dict:
        """
        Resolve conflicts between two data versions.

        Args:
            data_a: First data version.
            data_b: Second data version.

        Returns:
            The resolved data with highest version, or timestamp-based tiebreaker.
        """
        version_a = data_a.get("version", 0)
        version_b = data_b.get("version", 0)

        if version_a > version_b:
            return data_a
        elif version_b > version_a:
            return data_b

        timestamp_a = data_a.get("updated_at") or data_a.get("created_at", "")
        timestamp_b = data_b.get("updated_at") or data_b.get("created_at", "")

        if timestamp_a and timestamp_b:
            if timestamp_a > timestamp_b:
                return data_a
            elif timestamp_b > timestamp_a:
                return data_b

        return data_a

    @staticmethod
    def resolve_multiple(versions: list[dict]) -> dict:
        """
        Resolve conflicts between multiple data versions.

        Args:
            versions: List of data versions to resolve.

        Returns:
            The resolved data.
        """
        if not versions:
            return {}

        resolved = versions[0]
        for version in versions[1:]:
            resolved = ConflictResolution.resolve(resolved, version)

        return resolved


class MessageHasher:
    """Utility for hashing sync messages."""

    @staticmethod
    def compute_hash(message_data: dict) -> str:
        """
        Compute SHA-256 hash of message data.

        Args:
            message_data: Dictionary containing message data.

        Returns:
            Hex-encoded hash string.
        """
        data_str = str(sorted(message_data.items()))
        return hashlib.sha256(data_str.encode()).hexdigest()

    @staticmethod
    def compute_merkle_root(items: list[dict]) -> str:
        """
        Compute Merkle root of a list of items.

        Args:
            items: List of items to compute root from.

        Returns:
            Hex-encoded Merkle root.
        """
        if not items:
            return hashlib.sha256(b"").hexdigest()

        hashes = [MessageHasher.compute_hash(item) for item in items]

        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])

            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())

            hashes = new_hashes

        return hashes[0] if hashes else hashlib.sha256(b"").hexdigest()


class ProofOfWork:
    """Proof of work utility for message validation."""

    DIFFICULTY = 4

    @staticmethod
    def compute(data: dict, target_difficulty: int = None) -> tuple[str, int]:
        """
        Compute proof of work for message data.

        Args:
            data: Data to compute PoW for.
            target_difficulty: Number of leading zeros required (default: DIFFICULTY).

        Returns:
            Tuple of (hash, nonce).
        """
        target = target_difficulty or ProofOfWork.DIFFICULTY
        nonce = 0
        prefix = "0" * target

        while True:
            work_data = {**data, "nonce": nonce}
            hash_result = MessageHasher.compute_hash(work_data)

            if hash_result.startswith(prefix):
                return hash_result, nonce

            nonce += 1
            if nonce > 1e6:
                raise ValueError(
                    "Proof of work computation failed - too many iterations"
                )

    @staticmethod
    def verify(
        data: dict, hash_result: str, nonce: int, target_difficulty: int = None
    ) -> bool:
        """
        Verify proof of work.

        Args:
            data: Data that was hashed.
            hash_result: Hash result to verify.
            nonce: Nonce that was used.
            target_difficulty: Expected difficulty level.

        Returns:
            True if valid, False otherwise.
        """
        target = target_difficulty or ProofOfWork.DIFFICULTY
        prefix = "0" * target

        work_data = {**data, "nonce": nonce}
        computed = MessageHasher.compute_hash(work_data)

        return computed.startswith(prefix) and computed == hash_result


TRUST_THRESHOLDS = {
    "low": 0.0,
    "medium": 0.4,
    "high": 0.7,
    "very_high": 0.9,
}


class TrustScorer:
    """
    Calculate trust scores for issuers based on metrics and endorsements.
    """

    WEIGHTS = {
        "verification_success_rate": 0.30,
        "peer_endorsements": 0.20,
        "time_since_first_issuance": 0.15,
        "unique_holders": 0.15,
        "scope_violations": -0.20,
    }

    @classmethod
    def calculate_score(cls, metrics) -> float:
        """
        Calculate trust score for an issuer.

        Args:
            metrics: IssuerMetrics instance.

        Returns:
            Score between 0.0 and 1.0.
        """
        score = 0.0

        verification_score = metrics.verification_success_rate
        score += verification_score * cls.WEIGHTS["verification_success_rate"]

        endorsement_score = cls._calculate_endorsement_score(
            metrics.issuer_did, metrics.scope
        )
        score += endorsement_score * cls.WEIGHTS["peer_endorsements"]

        age_score = cls._calculate_age_score(metrics)
        score += age_score * cls.WEIGHTS["time_since_first_issuance"]

        breadth_score = cls._calculate_breadth_score(metrics.unique_holders)
        score += breadth_score * cls.WEIGHTS["unique_holders"]

        if metrics.scope_violations > 0:
            violation_penalty = min(metrics.scope_violations * 0.05, 0.5) * abs(
                cls.WEIGHTS["scope_violations"]
            )
            score -= violation_penalty

        return max(0.0, min(1.0, score))

    @classmethod
    def _calculate_endorsement_score(cls, issuer_did: str, scope) -> float:
        """
        Calculate endorsement score based on peer reviews.
        """
        from apps.core.models import IssuerEndorsement

        endorsements = IssuerEndorsement.objects.filter(
            endorsed_issuer_did=issuer_did,
            scope=scope,
            is_positive=True,
            is_active=True,
        )

        return len(endorsements) / (len(endorsements) + 5)

    @classmethod
    def _calculate_age_score(cls, metrics) -> float:
        """
        Calculate age score (logarithmic, caps at 1 year).
        """
        if not metrics.first_issuance:
            return 0.0

        days_since_first = (datetime.datetime.utcnow() - metrics.first_issuance).days

        if days_since_first <= 0:
            return 0.0

        return min(1.0, math.log(days_since_first + 1) / math.log(366))

    @classmethod
    def _calculate_breadth_score(cls, unique_holders: int) -> float:
        """
        Calculate breadth score based on unique holders.
        """
        if unique_holders <= 0:
            return 0.0
        return min(1.0, math.log(unique_holders + 1) / math.log(10001))

    @classmethod
    def get_trust_level(cls, score: float) -> str:
        """
        Get trust level string from score.

        Args:
            score: Trust score between 0.0 and 1.0.

        Returns:
            Trust level string: 'low', 'medium', 'high', or 'very_high'.
        """
        if score >= TRUST_THRESHOLDS["very_high"]:
            return "very_high"
        elif score >= TRUST_THRESHOLDS["high"]:
            return "high"
        elif score >= TRUST_THRESHOLDS["medium"]:
            return "medium"
        else:
            return "low"

    @classmethod
    def meets_threshold(cls, metrics, threshold: str) -> bool:
        """
        Check if issuer meets a trust threshold.

        Args:
            metrics: IssuerMetrics instance.
            threshold: Threshold name ('low', 'medium', 'high', 'very_high').

        Returns:
            True if score meets the threshold.
        """
        threshold_value = TRUST_THRESHOLDS.get(threshold, 0.0)
        score = cls.calculate_score(metrics)
        return score >= threshold_value
