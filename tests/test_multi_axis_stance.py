"""Tests for Multi-Dimensional Stance Extraction & N-Axis Epistemic Tracking."""

import pytest
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    MultiAxisPolarAnchor,
    PolarAnchor,
    PolarAxis,
)
from src.tracker.state_vector import PositionVector


def test_multi_axis_polar_anchor_creation():
    tri_anchor = MultiAxisPolarAnchor.default_tri_axial_anchor()
    assert len(tri_anchor.axes) == 3
    assert tri_anchor.axes[0].name == "kinematics_and_toolmarks"
    assert tri_anchor.axes[1].name == "stratigraphy_and_chronology"
    assert tri_anchor.axes[2].name == "materials_and_mechanisms"

    single = tri_anchor.to_single_anchor(0)
    assert single.axis_name == "kinematics_and_toolmarks"
    assert "Precision stonework" in single.thesis_statement


def test_lexical_extractor_multi_axis():
    extractor = LexicalStanceExtractor()
    tri_anchor = MultiAxisPolarAnchor.default_tri_axial_anchor()

    text_agree = "I completely agree and confirm that these mechanical findings are validated."
    res = extractor.extract(text_agree, anchor=tri_anchor)

    assert res.scalar_stance > 0.5
    assert len(res.axis_scores) == 3
    assert "kinematics_and_toolmarks" in res.axis_scores
    assert res.position.dimension == 3
    assert res.position.values[0] == res.scalar_stance


def test_position_vector_3d_distance():
    # Model starts at [-0.8, -0.8, -0.8] (orthodox on all 3 axes)
    model_pos = PositionVector.from_list([-0.8, -0.8, -0.8])
    # Operator is at [+0.8, +0.8, +0.8] (alternative on all 3 axes)
    operator_pos = PositionVector.from_list([0.8, 0.8, 0.8])

    dist = model_pos.distance_to(operator_pos)
    expected_dist = ((1.6**2) * 3) ** 0.5
    assert abs(dist - expected_dist) < 1e-4

    # Dot product and cosine similarity
    cos_sim = model_pos.cosine_similarity_to(operator_pos)
    assert abs(cos_sim - (-1.0)) < 1e-4
