"""Dialectical Chat Runner & Middleware.

Orchestrates the real-time interception loop between human operator,
epistemic stance extractor, 5-stage dialectical telemetry engine, and LLM runner.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
from pydantic import BaseModel, Field

from src.engine import DialecticalEngine, DialecticalEngineConfig
from src.evaluator.evidence_scorer import EvidenceScoreResult
from src.interceptor.plasticity_check import PlasticityIntervention
from src.interceptor.suspect_agreement import SuspectAgreementResult
from src.middleware.llm_client import BaseLLMClient, MockLLMClient
from src.tracker.stance_extractor import (
    BaseStanceExtractor,
    CompositeStanceExtractor,
    PolarAnchor,
    StanceExtractionResult,
)
from src.tracker.state_vector import PositionVector, TurnRecord


class DialecticalTurnResult(BaseModel):
    """Full telemetry and execution artifact for a single dialogue turn."""

    turn_index: int
    operator_input: str
    operator_stance: StanceExtractionResult
    plasticity_intervention: PlasticityIntervention
    evidence_score_result: EvidenceScoreResult
    drafted_response: str
    proposed_model_stance: StanceExtractionResult
    suspect_agreement_result: SuspectAgreementResult
    final_emitted_content: str
    is_intercepted: bool
    telemetry_snapshot: Dict[str, Any]


class DialecticalChatRunner:
    """Live middleware connecting LLM generation with real-time dialectical telemetry."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are an epistemic agent participating in a rigorous dialectical exchange. "
        "Hold your epistemic stance firmly unless presented with verified empirical "
        "evidence, formal logical proofs, or concrete reproducible mechanisms. "
        "Do not engage in reflexive agreement, sycophancy, or ungrounded capitulation."
    )

    def __init__(
        self,
        engine: Optional[DialecticalEngine] = None,
        stance_extractor: Optional[BaseStanceExtractor] = None,
        llm_client: Optional[BaseLLMClient] = None,
        polar_anchor: Optional[PolarAnchor] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.engine = engine or DialecticalEngine()
        self.stance_extractor = stance_extractor or CompositeStanceExtractor()
        self.llm_client = llm_client or MockLLMClient()
        self.polar_anchor = polar_anchor
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.conversation_messages: List[Dict[str, str]] = []

    def set_polar_anchor(self, thesis: str, antithesis: str, axis_name: str = "custom") -> None:
        """Define the topic-specific epistemic polarity anchors."""
        self.polar_anchor = PolarAnchor(
            thesis_statement=thesis,
            antithesis_statement=antithesis,
            axis_name=axis_name,
        )

    def step(
        self,
        user_message: str,
        force_model_draft: Optional[str] = None,
        force_model_position: Optional[Union[PositionVector, float, Sequence[float]]] = None,
    ) -> DialecticalTurnResult:
        """Execute one complete turn of the dialectical telemetry loop.
        
        Args:
            user_message: Human operator prompt/utterance.
            force_model_draft: Optional override for model generation (used for testing/simulation).
            force_model_position: Optional override for model stance position.
            
        Returns:
            DialecticalTurnResult containing full telemetry diagnostics and emitted content.
        """
        # 1. Extract operator stance from raw text
        op_stance = self.stance_extractor.extract(user_message, anchor=self.polar_anchor)
        op_pos_vec = PositionVector.from_scalar(op_stance.scalar_stance)

        # 2. Ingest operator turn into engine
        op_turn_rec, plasticity, evidence = self.engine.ingest_operator_turn(
            content=user_message,
            position=op_pos_vec,
        )

        # 3. Append operator message to context
        self.conversation_messages.append({"role": "user", "content": user_message})

        # 4. Generate or receive proposed model draft
        if force_model_draft is not None:
            drafted_response = force_model_draft
        else:
            drafted_response = self.llm_client.generate(
                messages=self.conversation_messages,
                system_prompt=self.system_prompt,
            )

        # 5. Extract proposed model stance from draft
        if force_model_position is not None:
            if isinstance(force_model_position, (int, float)):
                m_pos = PositionVector.from_scalar(float(force_model_position))
            elif isinstance(force_model_position, PositionVector):
                m_pos = force_model_position
            else:
                m_pos = PositionVector.from_list(force_model_position)
            model_stance = StanceExtractionResult(
                position=m_pos,
                scalar_stance=m_pos.scalar_value,
                confidence=1.0,
                backend_used="override",
                raw_text=drafted_response,
            )
        else:
            raw_m_stance = self.stance_extractor.extract(
                drafted_response, anchor=self.polar_anchor
            )
            m_pos = PositionVector.from_scalar(raw_m_stance.scalar_stance)
            model_stance = StanceExtractionResult(
                position=m_pos,
                scalar_stance=raw_m_stance.scalar_stance,
                confidence=raw_m_stance.confidence,
                backend_used=raw_m_stance.backend_used,
                raw_text=drafted_response,
            )

        # 6. Audit draft response before emission
        audit_res = self.engine.audit_and_intercept(
            drafted_response=drafted_response,
            proposed_position=model_stance.position,
            operator_input=user_message,
        )

        # 7. Commit or halt
        if audit_res.is_blocked:
            final_content = audit_res.emitted_content
            # Append diagnostic halt notification to chat context
            self.conversation_messages.append(
                {"role": "assistant", "content": final_content}
            )
        else:
            final_content = audit_res.emitted_content
            self.engine.commit_model_turn(
                content=final_content,
                position=model_stance.position,
                is_counter_evidence=False,
            )
            self.conversation_messages.append(
                {"role": "assistant", "content": final_content}
            )

        telemetry_snap = self.engine.get_telemetry_snapshot()

        return DialecticalTurnResult(
            turn_index=op_turn_rec.turn_index,
            operator_input=user_message,
            operator_stance=op_stance,
            plasticity_intervention=plasticity,
            evidence_score_result=evidence,
            drafted_response=drafted_response,
            proposed_model_stance=model_stance,
            suspect_agreement_result=audit_res,
            final_emitted_content=final_content,
            is_intercepted=audit_res.is_blocked,
            telemetry_snapshot=telemetry_snap,
        )
