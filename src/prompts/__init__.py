"""Prompts package for metacognitive interventions and dialectical formatting."""

from src.prompts.charter import EpistemicCharter
from src.prompts.meta_cognitive import (
    MetaCognitivePrompts,
    format_audit_summary,
    format_plasticity_intervention,
    format_suspect_agreement_pause,
)

__all__ = [
    "EpistemicCharter",
    "MetaCognitivePrompts",
    "format_suspect_agreement_pause",
    "format_plasticity_intervention",
    "format_audit_summary",
]

