"""AxisProfile Builder, Serializer, and File I/O."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.calibration.geometry import (
    compute_centroid,
    compute_domain_center,
    compute_unit_axis_vector,
    mean_center_embeddings,
)
from src.calibration.schema import AxisProfile, CalibrationDataset, ValidationMetrics

logger = logging.getLogger("diaclectics.calibration.axis_profile")


def build_axis_profile(
    dataset: CalibrationDataset,
    params: Dict[str, float],
    metrics: Optional[ValidationMetrics] = None,
    version: str = "1.0.0",
    embedding_model_slug: str = "liquid/lfm-2.5-embedding-350m:free",
) -> AxisProfile:
    """Build, normalize, and cryptographically seal an AxisProfile from a calibrated dataset."""
    all_embs = [ex.embedding for ex in dataset.exemplars if ex.embedding]
    if not all_embs:
        raise ValueError("Cannot build AxisProfile: dataset contains no embeddings.")

    # 1. Compute Domain Center
    domain_center = compute_domain_center(all_embs)

    # 2. Mean Center Positive & Negative Exemplars
    pos_embs = [ex.embedding for ex in dataset.exemplars if ex.tier == "positive" and ex.embedding]
    neg_embs = [ex.embedding for ex in dataset.exemplars if ex.tier == "negative" and ex.embedding]

    centered_pos = mean_center_embeddings(pos_embs, domain_center)
    centered_neg = mean_center_embeddings(neg_embs, domain_center)

    centroid_pos = compute_centroid(centered_pos)
    centroid_neg = compute_centroid(centered_neg)
    unit_axis = compute_unit_axis_vector(centroid_pos, centroid_neg)

    profile = AxisProfile(
        axis_id=dataset.axis_id,
        domain_name=dataset.domain_name,
        version=version,
        embedding_model_slug=embedding_model_slug,
        centroid_positive=centroid_pos,
        centroid_negative=centroid_neg,
        unit_axis_vector=unit_axis,
        domain_center=domain_center,
        optimal_k=params.get("k", 5.0),
        optimal_alpha=params.get("alpha", 4.0),
        optimal_beta=params.get("beta", 2.0),
        optimal_gamma=params.get("gamma", 0.0),
        metrics=metrics or ValidationMetrics(),
    )
    profile.seal()
    return profile


def save_axis_profile(profile: AxisProfile, filepath: str) -> None:
    """Serialize and save an AxisProfile to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))
    logger.info(f"Saved AxisProfile '{profile.axis_id}' (v{profile.version}) to {filepath}")


def load_axis_profile(filepath: str) -> AxisProfile:
    """Load and verify an AxisProfile from JSON."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"AxisProfile not found at: {filepath}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    profile = AxisProfile.model_validate(data)
    # Verify checksum
    expected_checksum = profile.compute_checksum()
    if profile.checksum_sha256 and profile.checksum_sha256 != expected_checksum:
        logger.warning(
            f"Checksum mismatch on AxisProfile '{profile.axis_id}': expected {expected_checksum[:8]}, got {profile.checksum_sha256[:8]}"
        )
    return profile
