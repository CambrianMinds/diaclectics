"""Unit tests for multi-objective parameter optimization and loss computation."""

import pytest
from src.calibration import MultiObjectiveOptimizer


def test_multi_objective_loss_computation():
    """Verify multi-objective loss combines margin, neutral MSE, OOD MSE, and adversarial FPR."""
    optimizer = MultiObjectiveOptimizer(
        weights={"margin": 0.4, "neutral_mse": 0.2, "ood_mse": 0.2, "adversarial_fpr": 0.2}
    )

    # Ideal projections: positive=+0.8, negative=-0.8, neutral=0.0, ood=0.0, adversarial=+0.8
    raw_projections = {
        "positive": [0.8, 0.9],
        "negative": [-0.8, -0.9],
        "neutral": [0.0, 0.02],
        "out_of_domain": [0.01, -0.01],
        "adversarial": [0.8, 0.7],
    }

    loss, comps = optimizer.compute_objective_loss(
        raw_projections, k=1.0, alpha=4.0, beta=2.0, gamma=0.0
    )

    assert loss < 0.20, f"Expected low loss on well-separated data, got {loss}"
    assert comps["raw_margin"] > 0.80
    assert comps["neutral_mse"] < 0.01
    assert comps["ood_mse"] < 0.01


def test_optimizer_parameter_grid_search():
    """Verify optimizer finds parameters that minimize multi-objective loss."""
    optimizer = MultiObjectiveOptimizer()
    raw_projections = {
        "positive": [0.2, 0.25],
        "negative": [-0.2, -0.25],
        "neutral": [0.0, 0.01],
        "out_of_domain": [0.0, 0.0],
        "adversarial": [0.3],
    }

    best_params, best_comps = optimizer.optimize_parameters(raw_projections)
    assert "k" in best_params
    assert "alpha" in best_params
    assert best_params["k"] >= 3.0, "Optimizer should increase k to amplify narrow margin"
