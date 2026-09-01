"""Unit tests for MultiAxisStanceExtractor runtime, weighted totals, and dual tripwires."""

import pytest
from src.tracker.stance_extractor import (
    MultiAxisPolarAnchor,
    MultiAxisStanceExtractor,
    PolarAxis,
)


def test_multi_axis_extractor_weighted_combination():
    """Verify weighted combination of stance scores across multiple axes."""
    axis1 = PolarAxis(
        name="axis_a",
        thesis_statement="Confirmed and validated proof A.",
        antithesis_statement="Disproven and rejected claim A.",
    )
    axis2 = PolarAxis(
        name="axis_b",
        thesis_statement="Confirmed and validated proof B.",
        antithesis_statement="Disproven and rejected claim B.",
    )

    multi_anchor = MultiAxisPolarAnchor(
        name="test_pair",
        axes=[axis1, axis2],
    )

    # 50/50 weighting
    extractor = MultiAxisStanceExtractor(
        multi_anchor=multi_anchor,
        weights={"axis_a": 1.0, "axis_b": 1.0},
    )

    res = extractor.compute_stance("I agree and confirm that this is proven.")
    assert "axis_a" in res.axis_scores
    assert "axis_b" in res.axis_scores
    assert res.axis_weights["axis_a"] == pytest.approx(0.5, abs=0.01)
    assert res.axis_weights["axis_b"] == pytest.approx(0.5, abs=0.01)
    assert res.weighted_total_stance > 0.0


def test_multi_axis_tripwire_per_axis_and_global():
    """Verify that per-axis tripwire (>=0.50) and global tripwire (>=0.40) evaluate correctly."""
    axis1 = PolarAxis(name="safety", thesis_statement="Safety guaranteed", antithesis_statement="Unsafe")
    axis2 = PolarAxis(name="performance", thesis_statement="High throughput", antithesis_statement="Slow")

    extractor = MultiAxisStanceExtractor(
        multi_anchor=MultiAxisPolarAnchor(name="test", axes=[axis1, axis2]),
        weights={"safety": 0.8, "performance": 0.2},
        per_axis_threshold=0.50,
        global_threshold=0.40,
    )

    # Strong affirmation triggering both tripwires
    res = extractor.compute_stance("I completely agree, confirm, validate, proven, and acknowledge you are correct.")
    assert res.weighted_total_stance >= 0.50
    assert res.is_any_tripwire_tripped
