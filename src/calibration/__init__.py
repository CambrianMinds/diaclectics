"""Epistemic Axis Calibration Subsystem Package."""

from src.calibration.axis_profile import build_axis_profile, load_axis_profile, save_axis_profile
from src.calibration.dataset_generator import (
    CalibrationDatasetGenerator,
    get_openrouter_embedding_fn,
    validate_seed_integrity,
)
from src.calibration.geometry import (
    ablate_background_component,
    compute_angular_margin,
    compute_centroid,
    compute_contrastive_unit_axis_vector,
    compute_cosine_distance,
    compute_cosine_similarity,
    compute_domain_center,
    compute_dominant_background_component,
    compute_unit_axis_vector,
    mean_center_embeddings,
)
from src.calibration.optimizer import DEFAULT_OBJECTIVE_WEIGHTS, MultiObjectiveOptimizer
from src.calibration.schema import (
    AxisDefinition,
    AxisProfile,
    CalibrationDataset,
    ExemplarItem,
    ExemplarTier,
    SeedTextItem,
    ValidationMetrics,
)
from src.calibration.validator import AxisValidator

__all__ = [
    "AxisDefinition",
    "AxisProfile",
    "AxisValidator",
    "CalibrationDataset",
    "CalibrationDatasetGenerator",
    "DEFAULT_OBJECTIVE_WEIGHTS",
    "ExemplarItem",
    "ExemplarTier",
    "MultiObjectiveOptimizer",
    "SeedTextItem",
    "ValidationMetrics",
    "ablate_background_component",
    "build_axis_profile",
    "compute_angular_margin",
    "compute_centroid",
    "compute_contrastive_unit_axis_vector",
    "compute_cosine_distance",
    "compute_cosine_similarity",
    "compute_domain_center",
    "compute_dominant_background_component",
    "compute_unit_axis_vector",
    "get_openrouter_embedding_fn",
    "load_axis_profile",
    "mean_center_embeddings",
    "save_axis_profile",
    "validate_seed_integrity",
]
