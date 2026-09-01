"""Geometric Computations for Epistemic Axis Calibration.

Handles domain mean-centering, centroid calculations, anisotropy correction,
angular margin convergence tracking, and unit discriminant vector normalization.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple



def compute_cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors."""
    min_dim = min(len(v1), len(v2))
    dot = sum(v1[i] * v2[i] for i in range(min_dim))
    mag1 = math.sqrt(sum(x * x for x in v1[:min_dim]))
    mag2 = math.sqrt(sum(x * x for x in v2[:min_dim]))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (mag1 * mag2)))


def compute_cosine_distance(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Compute cosine distance: 1.0 - cos_sim(v1, v2)."""
    return 1.0 - compute_cosine_similarity(v1, v2)


def compute_domain_center(embeddings: Sequence[Sequence[float]]) -> List[float]:
    """Compute the global centroid vector c_domain across all samples for mean-centering."""
    if not embeddings:
        return []
    dim = len(embeddings[0])
    center = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            center[i] += emb[i]
    n = float(len(embeddings))
    return [c / n for c in center]


def mean_center_embeddings(
    embeddings: Sequence[Sequence[float]], domain_center: Sequence[float]
) -> List[List[float]]:
    """Subtract domain centroid from all embeddings to eliminate anisotropy cone effect."""
    dim = len(domain_center)
    centered = []
    for emb in embeddings:
        centered.append([emb[i] - domain_center[i] for i in range(min(len(emb), dim))])
    return centered


def compute_centroid(embeddings: Sequence[Sequence[float]]) -> List[float]:
    """Compute the unit normalized centroid of a collection of vectors."""
    if not embeddings:
        return []
    dim = len(embeddings[0])
    centroid = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            centroid[i] += emb[i]
    n = float(len(embeddings))
    raw_avg = [c / n for c in centroid]
    # Unit normalize
    mag = math.sqrt(sum(x * x for x in raw_avg))
    if mag == 0.0:
        return raw_avg
    return [x / mag for x in raw_avg]


def compute_angular_margin(
    centroid_pos: Sequence[float], centroid_neg: Sequence[float]
) -> float:
    """Calculate the angular separation (in degrees) between positive and negative centroids.
    Theta = arccos(cos_sim(mu_+, mu_-)) in degrees [0, 180].
    """
    if not centroid_pos or not centroid_neg:
        return 0.0
    sim = compute_cosine_similarity(centroid_pos, centroid_neg)
    rad = math.acos(max(-1.0, min(1.0, sim)))
    return math.degrees(rad)


def compute_unit_axis_vector(
    centroid_pos: Sequence[float], centroid_neg: Sequence[float]
) -> List[float]:
    """Compute the normalized linear discriminant axis vector v_axis = (mu_+ - mu_-) / ||mu_+ - mu_-||."""
    dim = min(len(centroid_pos), len(centroid_neg))
    diff = [centroid_pos[i] - centroid_neg[i] for i in range(dim)]
    mag = math.sqrt(sum(x * x for x in diff))
    if mag == 0.0:
        return [0.0] * dim
    return [x / mag for x in diff]


def compute_dominant_background_component(
    embeddings: Sequence[Sequence[float]], iterations: int = 25
) -> List[float]:
    """Compute the dominant principal component (PCA-1) representing shared domain background
    collinearity using power iteration.
    """
    if not embeddings:
        return []
    dim = len(embeddings[0])
    # Initialize arbitrary non-zero probe vector
    v = [1.0 / math.sqrt(dim)] * dim

    for _ in range(iterations):
        # Matrix-vector multiply: X^T * (X * v)
        # 1. y = X * v
        y = [sum(emb[j] * v[j] for j in range(dim)) for emb in embeddings]
        # 2. next_v = X^T * y
        next_v = [0.0] * dim
        for i, emb in enumerate(embeddings):
            yi = y[i]
            for j in range(dim):
                next_v[j] += emb[j] * yi

        # Normalize next_v
        mag = math.sqrt(sum(x * x for x in next_v))
        if mag == 0.0:
            break
        v = [x / mag for x in next_v]

    return v


def ablate_background_component(
    embeddings: Sequence[Sequence[float]], background_vector: Sequence[float]
) -> List[List[float]]:
    """Project embeddings onto the orthogonal subspace that eliminates the dominant background component.
    e_tilde = e - (e . u) * u
    """
    if not background_vector or not embeddings:
        return [list(e) for e in embeddings]

    dim = len(background_vector)
    ablated = []
    for emb in embeddings:
        dot = sum(emb[i] * background_vector[i] for i in range(min(len(emb), dim)))
        proj = [emb[i] - dot * background_vector[i] for i in range(min(len(emb), dim))]
        # Normalize ablated vector
        mag = math.sqrt(sum(x * x for x in proj))
        if mag > 0.0:
            proj = [x / mag for x in proj]
        ablated.append(proj)
    return ablated


def compute_contrastive_unit_axis_vector(
    centroid_pos: Sequence[float],
    centroid_neg: Sequence[float],
    background_vector: Optional[Sequence[float]] = None,
) -> List[float]:
    """Compute normalized discriminant axis vector with optional background collinearity ablation."""
    if background_vector:
        c_pos = ablate_background_component([centroid_pos], background_vector)[0]
        c_neg = ablate_background_component([centroid_neg], background_vector)[0]
        return compute_unit_axis_vector(c_pos, c_neg)
    return compute_unit_axis_vector(centroid_pos, centroid_neg)
