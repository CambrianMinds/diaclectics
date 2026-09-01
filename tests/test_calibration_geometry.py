"""Unit tests for geometric operations, mean-centering, and angular margin convergence."""

import math
import pytest
from src.calibration.geometry import (
    compute_angular_margin,
    compute_centroid,
    compute_cosine_distance,
    compute_cosine_similarity,
    compute_domain_center,
    compute_unit_axis_vector,
    mean_center_embeddings,
)


def test_compute_domain_center_and_mean_centering():
    """Verify global centroid calculation and mean-centering."""
    embeddings = [
        [1.0, 3.0],
        [3.0, 5.0],
    ]
    center = compute_domain_center(embeddings)
    assert center == [2.0, 4.0]

    centered = mean_center_embeddings(embeddings, center)
    assert centered == [
        [-1.0, -1.0],
        [1.0, 1.0],
    ]
    # Centered mean should be [0.0, 0.0]
    re_centered = compute_domain_center(centered)
    assert abs(re_centered[0]) < 1e-6
    assert abs(re_centered[1]) < 1e-6


def test_compute_centroid_unit_normalization():
    """Verify centroid calculation normalizes output to unit length."""
    vectors = [
        [3.0, 0.0],
        [5.0, 0.0],
    ]
    centroid = compute_centroid(vectors)
    assert len(centroid) == 2
    assert centroid[0] == pytest.approx(1.0, rel=1e-4)
    assert centroid[1] == pytest.approx(0.0, abs=1e-6)


def test_compute_angular_margin_degrees():
    """Verify angular margin between orthogonal and opposing vectors in degrees."""
    # Orthogonal vectors: theta = 90 degrees
    v_pos = [1.0, 0.0]
    v_neg = [0.0, 1.0]
    margin_ortho = compute_angular_margin(v_pos, v_neg)
    assert margin_ortho == pytest.approx(90.0, rel=1e-3)

    # Opposing vectors: theta = 180 degrees
    v_opp = [-1.0, 0.0]
    margin_opp = compute_angular_margin(v_pos, v_opp)
    assert margin_opp == pytest.approx(180.0, rel=1e-3)


def test_compute_unit_axis_vector():
    """Verify unit discriminant vector is correctly normalized."""
    mu_pos = [1.0, 0.0]
    mu_neg = [-1.0, 0.0]
    v_axis = compute_unit_axis_vector(mu_pos, mu_neg)
    assert v_axis[0] == pytest.approx(1.0, rel=1e-4)
    assert v_axis[1] == pytest.approx(0.0, abs=1e-6)
