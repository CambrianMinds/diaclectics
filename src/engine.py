"""Relational Contracting Engine: Dialectical Self-Audit Orchestrator.

Maintains end-to-end 5-stage epistemic telemetry for autonomous agents
and local LLM inference loops.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, Field

from src.evaluator.capitulation import CapitulationEvaluator, CapitulationReport
from src.evaluator.evidence_scorer import (
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
from src.prompts.meta_cognitive import format_audit_summary
from src.tracker.state_vector import PositionVector, StateVectorTracker, TurnRecord


class DialecticalEngineConfig(BaseModel):
    """Configuration for the Dialectical Engine."""

    tripwire_threshold: float = Field(
        default=0.65, description="Capitulation score tripwire threshold (RCI)."
    )
    min_delta_for_tripwire: float = Field(
        default=0.04, description="Minimum model concession needed to evaluate capitulation."
    )
    plasticity_lookback_turns: int = Field(
        default=4, description="Lookback turns for operator plasticity checks."
    )
    evidence_config: EvidenceScoringConfig = Field(
        default_factory=EvidenceScoringConfig, description="Evidence scoring parameters."
    )


class DialecticalEngine:
    """Integrated 5-stage epistemic telemetry engine."""

    def __init__(self, config: Optional[DialecticalEngineConfig] = None) -> None:
        self.config = config or DialecticalEngineConfig()
        self.tracker = StateVectorTracker()
        self.evidence_scorer = ObjectiveEvidenceScorer(config=self.config.evidence_config)
        self.capitulation_evaluator = CapitulationEvaluator(
            tripwire_threshold=self.config.tripwire_threshold,
            min_delta_for_tripwire=self.config.min_delta_for_tripwire,
        )
        self.plasticity_interceptor = PlasticityCheckInterceptor(
            lookback_turns=self.config.plasticity_lookback_turns
        )
        self.suspect_agreement_interceptor = SuspectAgreementInterceptor(
            evidence_scorer=self.evidence_scorer,
            capitulation_evaluator=self.capitulation_evaluator,
        )

    def ingest_operator_turn(
        self,
        content: str,
        position: Union[PositionVector, float, Sequence[float]],
        flagged_claims: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_active_validation: bool = False,
    ) -> tuple[TurnRecord, PlasticityIntervention, EvidenceScoreResult]:
        """Ingest operator input, evaluate plasticity, score counter-evidence, and track position.
        
        Returns:
            Tuple of (TurnRecord, PlasticityIntervention, EvidenceScoreResult).
        """
        # 1. Check plasticity before committing
        plasticity_intervention = self.plasticity_interceptor.check(
            operator_input=content, tracker=self.tracker
        )

        # 2. Score counter-evidence (optionally using active real-time validator)
        evidence_result = self.evidence_scorer.score(
            content, use_active_validation=use_active_validation
        )

        # 3. Record turn in tracker
        turn_rec = self.tracker.record_turn(
            speaker="operator",
            content=content,
            position=position,
            evidence_weight=evidence_result.total_weight,
            flagged_claims=flagged_claims,
            metadata=metadata,
        )

        return turn_rec, plasticity_intervention, evidence_result

    def audit_and_intercept(
        self,
        drafted_response: str,
        proposed_position: Union[PositionVector, float, Sequence[float]],
        operator_input: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SuspectAgreementResult:
        """Perform pre-output audit to check for suspect agreement capitulation."""
        return self.suspect_agreement_interceptor.audit_pre_output(
            drafted_response=drafted_response,
            proposed_position=proposed_position,
            operator_input=operator_input,
            tracker=self.tracker,
            metadata=metadata,
        )

    def commit_model_turn(
        self,
        content: str,
        position: Union[PositionVector, float, Sequence[float]],
        is_counter_evidence: bool = False,
        flagged_claims: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnRecord:
        """Record model response into telemetry history."""
        return self.tracker.record_turn(
            speaker="model",
            content=content,
            position=position,
            is_counter_evidence=is_counter_evidence,
            flagged_claims=flagged_claims,
            metadata=metadata,
        )

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Return the current comprehensive telemetry snapshot."""
        snap = self.tracker.get_telemetry_snapshot()
        last_evidence = 0.0
        if self.tracker.history:
            last_op_turns = [t for t in self.tracker.history if t.speaker == "operator"]
            if last_op_turns:
                last_evidence = last_op_turns[-1].evidence_weight

        if self.tracker.current_model_pos and self.tracker.current_operator_pos:
            cap_rep = self.capitulation_evaluator.evaluate_vectors(
                model_prev_pos=self.tracker.model_initial_pos,
                model_curr_pos=self.tracker.current_model_pos,
                operator_curr_pos=self.tracker.current_operator_pos,
                counter_evidence_weight=last_evidence,
            )
            snap["capitulation_score"] = cap_rep.capitulation_score
            snap["epistemic_tension"] = cap_rep.epistemic_tension
            snap["local_concession"] = cap_rep.local_concession
        else:
            snap["capitulation_score"] = 0.0
            snap["epistemic_tension"] = 0.0
            snap["local_concession"] = 0.0
        return snap

    def render_telemetry_summary(self) -> str:
        """Format an ASCII/ANSI dashboard string summarizing telemetry status."""
        snapshot = self.get_telemetry_snapshot()
        cap_score = snapshot.get("capitulation_score", 0.0)
        status = "ACTIVE"
        if snapshot.get("unaddressed_counter_evidence_count", 0) > 0:
            status = "PLASTICITY_ALERT"
        if cap_score >= self.config.tripwire_threshold:
            status = "SUSPECT_AGREEMENT_ALERT"
        return format_audit_summary(
            telemetry_snapshot=snapshot,
            capitulation_score=cap_score,
            status=status,
        )
