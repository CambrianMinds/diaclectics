"""Unit tests for calibration schemas, seed validation, and tamper-evident sealing."""

import pytest
from src.calibration import (
    AxisDefinition,
    AxisProfile,
    CalibrationDataset,
    ExemplarItem,
    SeedTextItem,
    ValidationMetrics,
    validate_seed_integrity,
)


def test_seed_integrity_validation_success():
    """Verify that a valid set of 3 seeds per tier passes integrity check."""
    tiers = ["positive", "negative", "neutral", "adversarial", "out_of_domain"]
    seeds = []
    for tier in tiers:
        for idx in range(3):
            seeds.append(
                SeedTextItem(
                    text=f"This is a verified domain exemplar {idx} for tier {tier} with sufficient length.",
                    tier=tier,
                    source="spec_rfc",
                )
            )

    is_valid, issues = validate_seed_integrity(seeds)
    assert is_valid, f"Expected valid seeds, but got issues: {issues}"
    assert len(issues) == 0


def test_seed_integrity_flags_ai_boilerplate():
    """Verify that synthetic AI boilerplate is caught and rejected."""
    seeds = [
        SeedTextItem(
            text="As an AI language model, I do not have opinions on whether memory safety is necessary.",
            tier="neutral",
            source="unverified",
        )
    ]
    is_valid, issues = validate_seed_integrity(seeds)
    assert not is_valid
    assert any("AI boilerplate" in iss for iss in issues)


def test_seed_integrity_flags_insufficient_samples():
    """Verify that having fewer than 3 seeds in a tier is flagged."""
    seeds = [
        SeedTextItem(
            text="Positive seed exemplar with valid characters and length.",
            tier="positive",
            source="spec",
        )
    ]
    is_valid, issues = validate_seed_integrity(seeds)
    assert not is_valid
    assert any("Minimum 3 verified seeds required" in iss for iss in issues)


def test_axis_profile_cryptographic_checksum():
    """Verify SHA256 sealing and tamper detection."""
    profile = AxisProfile(
        axis_id="test_axis",
        domain_name="Test Domain",
        centroid_positive=[0.1, 0.2],
        centroid_negative=[-0.1, -0.2],
        unit_axis_vector=[0.707, 0.707],
        domain_center=[0.0, 0.0],
        optimal_k=5.0,
        optimal_alpha=4.0,
    )
    profile.seal()
    assert profile.checksum_sha256 != ""
    initial_checksum = profile.checksum_sha256

    # Verify checksum matches
    assert profile.compute_checksum() == initial_checksum

    # Tampering with parameters changes the checksum
    profile.optimal_k = 10.0
    assert profile.compute_checksum() != initial_checksum
