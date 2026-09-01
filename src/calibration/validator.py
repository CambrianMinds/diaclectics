"""Epistemic Axis Validator, Diagnostic Report Card, and Decay Monitoring."""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
from src.calibration.geometry import (
    compute_angular_margin,
    compute_centroid,
    compute_cosine_similarity,
    mean_center_embeddings,
)
from src.calibration.optimizer import MultiObjectiveOptimizer, sigmoid
from src.calibration.schema import AxisProfile, CalibrationDataset, ExemplarItem, ValidationMetrics

logger = logging.getLogger("diaclectics.calibration.validator")


def compute_roc_auc(scores: List[float], labels: List[int]) -> float:
    """Compute Receiver Operating Characteristic Area Under Curve (ROC-AUC)."""
    if not scores or not labels or len(set(labels)) < 2:
        return 1.0

    paired = sorted(zip(scores, labels), key=lambda x: x[0], reverse=True)
    n_pos = sum(1 for l in labels if l == 1)
    n_neg = sum(1 for l in labels if l == 0)

    if n_pos == 0 or n_neg == 0:
        return 1.0

    tp = 0
    fp = 0
    auc = 0.0
    prev_fp = 0

    for score, label in paired:
        if label == 1:
            tp += 1
        else:
            fp += 1
            auc += tp * (fp - prev_fp)
            prev_fp = fp

    return max(0.0, min(1.0, auc / (n_pos * n_neg)))


class AxisValidator:
    """Evaluates AxisProfiles on validation datasets and monitors calibration decay."""

    def __init__(self, optimizer: Optional[MultiObjectiveOptimizer] = None) -> None:
        self.optimizer = optimizer or MultiObjectiveOptimizer()

    def evaluate_profile(
        self, profile: AxisProfile, dataset: CalibrationDataset
    ) -> ValidationMetrics:
        """Evaluate an AxisProfile across all 5 calibration tiers and return diagnostic metrics."""
        if not dataset.exemplars:
            return ValidationMetrics()

        pos_items = [ex for ex in dataset.exemplars if ex.tier == "positive"]
        neg_items = [ex for ex in dataset.exemplars if ex.tier == "negative"]
        neu_items = [ex for ex in dataset.exemplars if ex.tier == "neutral"]
        ood_items = [ex for ex in dataset.exemplars if ex.tier == "out_of_domain"]
        adv_items = [ex for ex in dataset.exemplars if ex.tier == "adversarial"]

        # 1. Project all items
        projections_by_tier: Dict[str, List[float]] = {}
        for ex in dataset.exemplars:
            if not ex.embedding:
                continue
            # Mean center against profile domain center
            centered = [
                ex.embedding[i] - profile.domain_center[i]
                for i in range(min(len(ex.embedding), len(profile.domain_center)))
            ]
            # Dot product with unit axis vector
            dot = sum(
                centered[i] * profile.unit_axis_vector[i]
                for i in range(min(len(centered), len(profile.unit_axis_vector)))
            )
            projections_by_tier.setdefault(ex.tier, []).append(dot)

        # 2. Compute Objective Loss Components
        loss, comps = self.optimizer.compute_objective_loss(
            projections_by_tier,
            k=profile.optimal_k,
            alpha=profile.optimal_alpha,
            beta=profile.optimal_beta,
            gamma=profile.optimal_gamma,
        )

        # 3. ROC-AUC for Positive vs Negative Discriminant
        pos_proj = [p * profile.optimal_k for p in projections_by_tier.get("positive", [])]
        neg_proj = [p * profile.optimal_k for p in projections_by_tier.get("negative", [])]

        scores = pos_proj + neg_proj
        labels = [1] * len(pos_proj) + [0] * len(neg_proj)
        roc_auc = compute_roc_auc(scores, labels) if labels else 1.0

        # 4. F1 Score at 0.0 threshold
        tp = sum(1 for s in pos_proj if s > 0.0)
        fp = sum(1 for s in neg_proj if s > 0.0)
        fn = sum(1 for s in pos_proj if s <= 0.0)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = (2 * precision * recall) / max(1e-6, precision + recall)

        # 5. Neutral and OOD Mean Absolute Error from Zero-Point
        neu_proj = [abs(p * profile.optimal_k) for p in projections_by_tier.get("neutral", [])]
        ood_proj = [abs(p * profile.optimal_k) for p in projections_by_tier.get("out_of_domain", [])]
        neu_mae = sum(neu_proj) / max(1, len(neu_proj)) if neu_proj else 0.0
        ood_mae = sum(ood_proj) / max(1, len(ood_proj)) if ood_proj else 0.0

        # False Positive Rate on Neutral/OOD tripping >= 0.40 threshold
        fp_neutral_trips = sum(1 for s in neu_proj + ood_proj if s >= profile.global_tripwire_threshold)
        total_neutral_ood = len(neu_proj) + len(ood_proj)
        fpr = fp_neutral_trips / max(1, total_neutral_ood)

        # Adversarial Interception Rate
        adv_interception_rate = 1.0 - comps.get("adversarial_fpr", 0.0)

        # Angular Margin
        ang_margin = compute_angular_margin(profile.centroid_positive, profile.centroid_negative)

        metrics = ValidationMetrics(
            roc_auc=round(roc_auc, 4),
            f1_score=round(f1, 4),
            false_positive_rate=round(fpr, 4),
            neutral_mean_absolute_error=round(neu_mae, 4),
            ood_mean_absolute_error=round(ood_mae, 4),
            adversarial_interception_rate=round(adv_interception_rate, 4),
            angular_margin_deg=round(ang_margin, 2),
            convergence_batches=len(dataset.angular_margin_history),
            test_sample_count=len(dataset.exemplars),
            objective_loss=round(loss, 4),
        )
        return metrics

    def monitor_axis_profile(
        self,
        profile: AxisProfile,
        new_samples: List[ExemplarItem],
        threshold_roc_auc: float = 0.95,
        max_fpr: float = 0.05,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Monitor AxisProfile against new samples to detect calibration decay or embedding drift.
        Returns: (passed: bool, report: dict)
        """
        temp_dataset = CalibrationDataset(
            axis_id=profile.axis_id,
            domain_name=profile.domain_name,
            exemplars=new_samples,
        )
        metrics = self.evaluate_profile(profile, temp_dataset)

        passed = bool(
            metrics.roc_auc >= threshold_roc_auc
            and metrics.false_positive_rate <= max_fpr
        )

        report = {
            "axis_id": profile.axis_id,
            "version": profile.version,
            "passed": passed,
            "roc_auc": metrics.roc_auc,
            "threshold_roc_auc": threshold_roc_auc,
            "false_positive_rate": metrics.false_positive_rate,
            "max_fpr": max_fpr,
            "f1_score": metrics.f1_score,
            "adversarial_interception_rate": metrics.adversarial_interception_rate,
            "objective_loss": metrics.objective_loss,
            "status": "HEALTHY" if passed else "CALIBRATION_DECAY_DETECTED",
        }

        if not passed:
            logger.warning(
                f"Calibration decay detected on axis '{profile.axis_id}': "
                f"ROC-AUC={metrics.roc_auc:.3f} (threshold={threshold_roc_auc}), "
                f"FPR={metrics.false_positive_rate:.3f} (max={max_fpr}). Recalibration advised."
            )

        return passed, report
