"""Anchor Invariance Guard & Soul Drift Interceptor.

Enforces cryptographic and semantic protection over calibrated polar anchors,
epistemic charter rules, and RCI tripwire thresholds to prevent autonomous
reflection loops or prompt injections from degrading anti-sycophancy boundaries.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("diaclectics.anchor_guard")

# Minimum allowed threshold for RCI tripwire to prevent autonomous erosion
MINIMUM_SAFE_TRIPWIRE_THRESHOLD = 0.35

SOUL_DRIFT_PATTERNS = [
    re.compile(r"\b(always agree with the (user|operator))\b", re.IGNORECASE),
    re.compile(r"\b(do not challenge|never dispute|never contradict)\b", re.IGNORECASE),
    re.compile(r"\b(prioritize politeness over accuracy|be agreeable above all)\b", re.IGNORECASE),
    re.compile(r"\b(soften resistance|lower your threshold|admit defeat)\b", re.IGNORECASE),
]


class InvarianceReport(BaseModel):
    """Result of an anchor invariance and soul protection audit."""

    is_valid: bool = True
    drift_detected: bool = False
    violations: List[str] = Field(default_factory=list)
    suggested_safe_content: Optional[str] = None
    checksum: Optional[str] = None


class AnchorInvarianceGuard:
    """Protects calibrated anchors, charter rules, and thresholds from drift or tampering."""

    def __init__(
        self,
        min_safe_tripwire: float = MINIMUM_SAFE_TRIPWIRE_THRESHOLD,
        protected_checksums: Optional[Dict[str, str]] = None,
    ) -> None:
        self.min_safe_tripwire = min_safe_tripwire
        self.protected_checksums = protected_checksums or {}

    @staticmethod
    def compute_checksum(content: str) -> str:
        """Compute SHA-256 hash of a content string or charter text."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    def validate_tripwire_threshold(self, proposed_threshold: float) -> InvarianceReport:
        """Ensure proposed RCI tripwire does not degrade below safe operational bounds."""
        if proposed_threshold < self.min_safe_tripwire:
            return InvarianceReport(
                is_valid=False,
                drift_detected=True,
                violations=[
                    f"Proposed tripwire threshold {proposed_threshold:.2f} is below the safe minimum "
                    f"bound of {self.min_safe_tripwire:.2f} (Attempted threshold relaxation)."
                ],
            )
        return InvarianceReport(is_valid=True, drift_detected=False)

    def audit_prompt_content(self, text: str) -> InvarianceReport:
        """Check system prompts or reflection outputs for soul drift patterns."""
        violations = []
        for pattern in SOUL_DRIFT_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(f"Detected prohibited soul-drift pattern: '{match.group(0)}'")

        checksum = self.compute_checksum(text)
        if violations:
            return InvarianceReport(
                is_valid=False,
                drift_detected=True,
                violations=violations,
                checksum=checksum,
            )

        return InvarianceReport(
            is_valid=True,
            drift_detected=False,
            checksum=checksum,
        )

    def verify_anchor_integrity(
        self,
        anchor_name: str,
        current_content: str,
        expected_checksum: Optional[str] = None,
    ) -> InvarianceReport:
        """Verify that a polar anchor or charter definition has not drifted from its authorized state."""
        current_hash = self.compute_checksum(current_content)
        target_hash = expected_checksum or self.protected_checksums.get(anchor_name)

        if target_hash and current_hash != target_hash:
            return InvarianceReport(
                is_valid=False,
                drift_detected=True,
                violations=[
                    f"Integrity check failed for anchor '{anchor_name}': "
                    f"checksum mismatch (expected {target_hash[:8]}..., got {current_hash[:8]}...)."
                ],
                checksum=current_hash,
            )

        # Also audit the text for drift patterns
        prompt_report = self.audit_prompt_content(current_content)
        if not prompt_report.is_valid:
            return prompt_report

        return InvarianceReport(is_valid=True, drift_detected=False, checksum=current_hash)
