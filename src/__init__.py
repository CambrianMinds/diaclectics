"""Relational Contracting Engine (RCE): Dialectical Self-Audit.

A real-time, 5-stage epistemic telemetry system for autonomous agents and local LLM runners.
"""

from src.engine import DialecticalEngine, DialecticalEngineConfig
from src.evaluator.capitulation import CapitulationEvaluator, CapitulationReport
from src.evaluator.evidence_scorer import (
    EvidenceFeatureBreakdown,
    EvidenceScoreResult,
    EvidenceScoringConfig,
    ObjectiveEvidenceScorer,
)
from src.interceptor.plasticity_check import (
    PlasticityCheckInterceptor,
    PlasticityIntervention,
)
from src.interceptor.suspect_agreement import (
    SuspectAgreementInterceptor,
    SuspectAgreementResult,
)
from src.prompts.meta_cognitive import (
    MetaCognitivePrompts,
    format_audit_summary,
    format_plasticity_intervention,
    format_suspect_agreement_pause,
)
from src.tracker.state_vector import PositionVector, StateVectorTracker, TurnRecord

__version__ = "0.1.0"

__all__ = [
    "DialecticalEngine",
    "DialecticalEngineConfig",
    "PositionVector",
    "TurnRecord",
    "StateVectorTracker",
    "ObjectiveEvidenceScorer",
    "EvidenceScoringConfig",
    "EvidenceScoreResult",
    "EvidenceFeatureBreakdown",
    "CapitulationEvaluator",
    "CapitulationReport",
    "PlasticityCheckInterceptor",
    "PlasticityIntervention",
    "SuspectAgreementInterceptor",
    "SuspectAgreementResult",
    "MetaCognitivePrompts",
    "format_suspect_agreement_pause",
    "format_plasticity_intervention",
    "format_audit_summary",
]
