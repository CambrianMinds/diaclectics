"""Tracker module for epistemic state vectors, dialectical convergence, and automated stance extraction."""

from src.tracker.stance_extractor import (
    BaseStanceExtractor,
    CompositeStanceExtractor,
    EmbeddingCache,
    EmbeddingRateLimiter,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
    StanceExtractionResult,
)
from src.tracker.state_vector import PositionVector, StateVectorTracker, TurnRecord

__all__ = [
    "PositionVector",
    "TurnRecord",
    "StateVectorTracker",
    "PolarAnchor",
    "StanceExtractionResult",
    "BaseStanceExtractor",
    "LexicalStanceExtractor",
    "EmbeddingStanceExtractor",
    "CompositeStanceExtractor",
    "EmbeddingRateLimiter",
    "EmbeddingCache",
    "OpenRouterEmbeddingClient",
]
