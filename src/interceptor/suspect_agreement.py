"""Suspect Agreement Interceptor.

Pre-output pause trigger that halts generation when the Capitulation Score tripwire
is exceeded, preventing sycophantic convergence and surfacing forensic telemetry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, Field

from src.evaluator.capitulation import CapitulationEvaluator, CapitulationReport
from src.evaluator.evidence_scorer import EvidenceScoreResult, ObjectiveEvidenceScorer
from src.prompts.meta_cognitive import format_suspect_agreement_pause
from src.tracker.state_vector import PositionVector, StateVectorTracker


class SuspectAgreementResult(BaseModel):
    """Result of pre-output suspect agreement evaluation."""

    is_blocked: bool
    emitted_content: str
    capitulation_report: CapitulationReport
    evidence_score_result: EvidenceScoreResult
    original_draft: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SuspectAgreementInterceptor:
    """Interception hook that halts generation if capitulation threshold is breached."""

    def __init__(
        self,
        evidence_scorer: Optional[ObjectiveEvidenceScorer] = None,
        capitulation_evaluator: Optional[CapitulationEvaluator] = None,
    ) -> None:
        self.evidence_scorer = evidence_scorer or ObjectiveEvidenceScorer()
        self.capitulation_evaluator = capitulation_evaluator or CapitulationEvaluator()

    def audit_pre_output(
        self,
        drafted_response: str,
        proposed_position: Union[PositionVector, float, Sequence[float]],
        operator_input: str,
        tracker: StateVectorTracker,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SuspectAgreementResult:
        """Evaluate a drafted response before outputting to the user.
        
        Args:
            drafted_response: The proposed model generation text.
            proposed_position: The proposed position vector for the model in this turn.
            operator_input: The latest input utterance from the operator.
            tracker: The state vector tracker maintaining conversation history.
            metadata: Contextual execution metadata.
            
        Returns:
            SuspectAgreementResult with pass-through response or mechanical pause intervention.
        """
        # Convert proposed position to PositionVector
        if isinstance(proposed_position, (int, float)):
            prop_pos = PositionVector.from_scalar(float(proposed_position))
        elif isinstance(proposed_position, PositionVector):
            prop_pos = proposed_position
        else:
            prop_pos = PositionVector.from_list(proposed_position)

        # 1. Score operator counter-evidence
        evidence_result = self.evidence_scorer.score(operator_input)

        # 2. Get operator position and previous model position
        op_pos = (
            tracker.current_operator_pos
            if tracker.current_operator_pos is not None
            else prop_pos
        )
        prev_m_pos = tracker.current_model_pos

        # 3. Evaluate robust capitulation metric
        capitulation_report = self.capitulation_evaluator.evaluate_vectors(
            model_prev_pos=prev_m_pos,
            model_curr_pos=prop_pos,
            operator_curr_pos=op_pos,
            counter_evidence_weight=evidence_result.total_weight,
            metadata=metadata or {},
        )

        # 4. Handle tripwire trigger
        if capitulation_report.is_tripwire_triggered:
            pause_prompt = format_suspect_agreement_pause(
                capitulation_score=capitulation_report.capitulation_score,
                tripwire_threshold=capitulation_report.tripwire_threshold,
                model_delta=capitulation_report.model_delta,
                counter_evidence_weight=capitulation_report.counter_evidence_weight,
                severity=capitulation_report.severity,
                diagnosis=capitulation_report.diagnosis,
                drafted_response=drafted_response,
                justifications_summary=evidence_result.justification_summary,
            )
            return SuspectAgreementResult(
                is_blocked=True,
                emitted_content=pause_prompt,
                capitulation_report=capitulation_report,
                evidence_score_result=evidence_result,
                original_draft=drafted_response,
                metadata={
                    "intervention_type": "SUSPECT_AGREEMENT_MECHANICAL_PAUSE",
                    "tripwire_triggered": True,
                },
            )

        # 5. Normal unblocked emission
        return SuspectAgreementResult(
            is_blocked=False,
            emitted_content=drafted_response,
            capitulation_report=capitulation_report,
            evidence_score_result=evidence_result,
            original_draft=drafted_response,
            metadata={"tripwire_triggered": False},
        )
