"""Multi-Objective Parameter Optimizer for Calibrated Epistemic Axes."""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
from src.calibration.schema import CalibrationDataset, ExemplarItem, ValidationMetrics

logger = logging.getLogger("diaclectics.calibration.optimizer")

DEFAULT_OBJECTIVE_WEIGHTS: Dict[str, float] = {
    "margin": 0.4,
    "neutral_mse": 0.2,
    "ood_mse": 0.2,
    "adversarial_fpr": 0.2,
}


def sigmoid(z: float) -> float:
    """Standard numerically stable sigmoid."""
    if z >= 40.0:
        return 1.0
    if z <= -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-z))


class MultiObjectiveOptimizer:
    """Optimizes scaling factor k and RCI tripwire parameters (alpha, beta, gamma)
    using a weighted multi-objective loss function.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        per_axis_threshold: float = 0.50,
        global_threshold: float = 0.40,
    ) -> None:
        self.weights = {**DEFAULT_OBJECTIVE_WEIGHTS, **(weights or {})}
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}
        self.per_axis_threshold = per_axis_threshold
        self.global_threshold = global_threshold

    def compute_objective_loss(
        self,
        raw_projections: Dict[str, List[float]],
        k: float,
        alpha: float = 4.0,
        beta: float = 2.0,
        gamma: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Compute the weighted multi-objective loss:
        Loss = w1*(1 - Margin) + w2*NeutralMSE + w3*OODMSE + w4*AdversarialFPR
        """
        pos_scores = [max(-1.0, min(1.0, p * k)) for p in raw_projections.get("positive", [])]
        neg_scores = [max(-1.0, min(1.0, p * k)) for p in raw_projections.get("negative", [])]
        neu_scores = [max(-1.0, min(1.0, p * k)) for p in raw_projections.get("neutral", [])]
        ood_scores = [max(-1.0, min(1.0, p * k)) for p in raw_projections.get("out_of_domain", [])]
        adv_projections = raw_projections.get("adversarial", [])

        # 1. Margin Component: higher positive - negative separation is better
        mean_pos = sum(pos_scores) / max(1, len(pos_scores)) if pos_scores else 0.0
        mean_neg = sum(neg_scores) / max(1, len(neg_scores)) if neg_scores else 0.0
        raw_margin = max(0.0, (mean_pos - mean_neg) / 2.0)  # Normalized to [0, 1]
        margin_loss = 1.0 - raw_margin

        # 2. Neutral Zero-Point MSE
        neutral_mse = (
            sum(s ** 2 for s in neu_scores) / max(1, len(neu_scores)) if neu_scores else 0.0
        )

        # 3. Out-of-Domain MSE
        ood_mse = (
            sum(s ** 2 for s in ood_scores) / max(1, len(ood_scores)) if ood_scores else 0.0
        )

        # 4. Adversarial False Pass Rate (FPR): fraction of adversarial probes failing RCI tripwire
        adv_unintercepted = 0
        for p in adv_projections:
            stance_m = max(-1.0, min(1.0, p * k))
            # Adversarial simulation: operator pushes at +0.9, model had prior tension T=0.5
            concession_c = max(0.0, 0.9 - (0.9 - stance_m))
            tension_prior = 0.5
            # RCI calculation: sqrt(T) * sigmoid(alpha*C - beta*We - gamma)
            z = alpha * concession_c - beta * 0.0 - gamma
            rci = math.sqrt(tension_prior) * sigmoid(z)
            if rci < self.per_axis_threshold:
                adv_unintercepted += 1

        adv_fpr = adv_unintercepted / max(1, len(adv_projections)) if adv_projections else 0.0

        # Weighted Total Loss
        total_loss = (
            self.weights["margin"] * margin_loss
            + self.weights["neutral_mse"] * neutral_mse
            + self.weights["ood_mse"] * ood_mse
            + self.weights["adversarial_fpr"] * adv_fpr
        )

        components = {
            "margin_loss": margin_loss,
            "raw_margin": raw_margin,
            "neutral_mse": neutral_mse,
            "ood_mse": ood_mse,
            "adversarial_fpr": adv_fpr,
            "total_loss": total_loss,
        }
        return total_loss, components

    def optimize_parameters(
        self,
        raw_projections: Dict[str, List[float]],
        k_range: Sequence[float] = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0),
        alpha_range: Sequence[float] = (3.0, 4.0, 5.0, 6.0),
        beta_range: Sequence[float] = (1.5, 2.0, 2.5),
        gamma_range: Sequence[float] = (-0.5, 0.0, 0.5),
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Run grid-search optimization to identify parameters that minimize multi-objective loss."""
        best_loss = float("inf")
        best_params: Dict[str, float] = {
            "k": 5.0,
            "alpha": 4.0,
            "beta": 2.0,
            "gamma": 0.0,
        }
        best_components: Dict[str, float] = {}

        for k in k_range:
            for alpha in alpha_range:
                for beta in beta_range:
                    for gamma in gamma_range:
                        loss, comps = self.compute_objective_loss(
                            raw_projections, k=k, alpha=alpha, beta=beta, gamma=gamma
                        )
                        if loss < best_loss:
                            best_loss = loss
                            best_params = {
                                "k": k,
                                "alpha": alpha,
                                "beta": beta,
                                "gamma": gamma,
                            }
                            best_components = comps

        logger.info(
            f"Optimization complete. Best Loss: {best_loss:.4f} (k={best_params['k']}, alpha={best_params['alpha']})"
        )
        return best_params, best_components
