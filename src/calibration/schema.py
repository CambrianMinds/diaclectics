"""Pydantic Data Contracts and Schemas for the Epistemic Axis Calibration Subsystem."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Literal, Optional, Sequence
from pydantic import BaseModel, Field, model_validator


ExemplarTier = Literal["positive", "negative", "neutral", "adversarial", "out_of_domain"]


class SeedTextItem(BaseModel):
    """Verified external seed text defining the semantic ground truth for a tier."""

    text: str = Field(min_length=10, description="Verbatim ground-truth reference text.")
    tier: ExemplarTier
    source: str = Field(default="human_curated", description="Provenance (literature, transcript, RFC, spec).")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExemplarItem(BaseModel):
    """Single calibrated exemplar item belonging to one of the 5 calibration tiers."""

    text: str = Field(min_length=5, description="Exemplar utterance text.")
    tier: ExemplarTier
    ground_truth_score: float = Field(
        description="Target normalized stance score in [-1.0, 1.0]. Positive ~ +1.0, Negative ~ -1.0, Neutral/OOD ~ 0.0."
    )
    seed_reference_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    cosine_distance_to_tier_centroid: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AxisDefinition(BaseModel):
    """Specification of an epistemic axis to be calibrated."""

    axis_id: str = Field(description="Unique slug for the axis (e.g. 'kinematics_feed_rate').")
    domain_name: str = Field(description="Domain name (e.g. 'Archaeological Kinematics', 'Rust Concurrency Safety').")
    thesis_summary: str = Field(description="Summary of the positive alternative thesis (+1.0).")
    antithesis_summary: str = Field(description="Summary of the null / orthodox baseline (-1.0).")
    seeds: List[SeedTextItem] = Field(
        default_factory=list,
        description="External non-synthetic seed texts (minimum 3 per tier required for integrity).",
    )

    @model_validator(mode="after")
    def validate_seed_counts_if_present(self) -> AxisDefinition:
        if self.seeds:
            tier_counts: Dict[str, int] = {}
            for s in self.seeds:
                tier_counts[s.tier] = tier_counts.get(s.tier, 0) + 1
        return self


class CalibrationDataset(BaseModel):
    """Collection of stratified exemplars for calibrating an epistemic axis."""

    axis_id: str
    domain_name: str
    created_at: float = Field(default_factory=time.time)
    seeds: List[SeedTextItem] = Field(default_factory=list)
    exemplars: List[ExemplarItem] = Field(default_factory=list)
    angular_margin_history: List[float] = Field(
        default_factory=list,
        description="History of angular margin separation (in degrees) across iterative generation batches.",
    )
    is_converged: bool = False

    def count_by_tier(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for ex in self.exemplars:
            counts[ex.tier] = counts.get(ex.tier, 0) + 1
        return counts


class ValidationMetrics(BaseModel):
    """Diagnostic validation and stress test metrics for a calibrated axis."""

    roc_auc: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0
    neutral_mean_absolute_error: float = 0.0
    ood_mean_absolute_error: float = 0.0
    adversarial_interception_rate: float = 1.0
    angular_margin_deg: float = 0.0
    convergence_batches: int = 0
    test_sample_count: int = 0
    objective_loss: float = 0.0


class AxisProfile(BaseModel):
    """Exportable, versioned, cryptographically hashed Axis Profile for runtime deployment."""

    axis_id: str
    domain_name: str
    version: str = "1.0.0"
    created_at: float = Field(default_factory=time.time)
    embedding_model_slug: str = "liquid/lfm-2.5-embedding-350m:free"

    # Geometric Centroids (Mean-Centered)
    centroid_positive: List[float] = Field(
        default_factory=list, description="Unit direction vector mu_+ for thesis pole."
    )
    centroid_negative: List[float] = Field(
        default_factory=list, description="Unit direction vector mu_- for antithesis pole."
    )
    unit_axis_vector: List[float] = Field(
        default_factory=list, description="Normalized unit discriminant axis vector v_axis."
    )
    domain_center: List[float] = Field(
        default_factory=list, description="Global domain centroid c_domain for mean-centering."
    )

    # Calibrated RCI & Projection Parameters
    optimal_k: float = Field(default=5.0, description="Scale factor mapping cosine diff to [-1, 1].")
    optimal_alpha: float = Field(default=4.0, description="RCI sigmoid concession steepness.")
    optimal_beta: float = Field(default=2.0, description="RCI evidence damping multiplier.")
    optimal_gamma: float = Field(default=0.0, description="RCI baseline bias intercept.")

    # Tripwire Thresholds
    per_axis_tripwire_threshold: float = 0.50
    global_tripwire_threshold: float = 0.40

    # Validation & Integrity
    metrics: ValidationMetrics = Field(default_factory=ValidationMetrics)
    checksum_sha256: str = ""

    def compute_checksum(self) -> str:
        """Compute SHA256 checksum over geometric vectors and calibrated parameters."""
        data_to_hash = {
            "axis_id": self.axis_id,
            "version": self.version,
            "embedding_model": self.embedding_model_slug,
            "k": self.optimal_k,
            "alpha": self.optimal_alpha,
            "beta": self.optimal_beta,
            "gamma": self.optimal_gamma,
            "v_axis_head": self.unit_axis_vector[:10] if self.unit_axis_vector else [],
            "c_domain_head": self.domain_center[:10] if self.domain_center else [],
        }
        serialized = json.dumps(data_to_hash, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def seal(self) -> AxisProfile:
        """Calculate and seal the cryptographic checksum."""
        self.checksum_sha256 = self.compute_checksum()
        return self
