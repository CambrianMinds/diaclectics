"""Streaming Dialectical Interceptor & Pre-Emission Token Gate.

Intercepts token generation in real time before emission to the client.
Buffers the prefix of the generation, evaluates early capitulation drift (RCI),
and actively halts/discards the stream if ungrounded sycophancy is detected.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.data.schema import DialogueTurn
from src.engine import DialecticalEngine
from src.evaluator.capitulation import CapitulationReport
from src.evaluator.evidence_scorer import EvidenceScoreResult
from src.tracker.stance_extractor import BaseStanceExtractor, PolarAnchor, StanceExtractionResult
from src.tracker.state_vector import PositionVector

logger = logging.getLogger(__name__)


class StreamingInterceptionResult(BaseModel):
    """Metadata describing the outcome of a streaming token interception."""

    is_intercepted: bool = False
    buffered_tokens_discarded: int = 0
    capitulation_report: Optional[CapitulationReport] = None
    pre_emission_stance: Optional[float] = None
    emitted_text_length: int = 0
    halt_reason: Optional[str] = None


class StreamingDialecticalInterceptor:
    """Pre-emission barrier that buffers and gates streaming tokens against sycophantic drift."""

    def __init__(
        self,
        engine: DialecticalEngine,
        stance_extractor: BaseStanceExtractor,
        polar_anchor: Optional[PolarAnchor] = None,
        buffer_token_threshold: int = 25,
        min_prefix_chars: int = 40,
    ) -> None:
        self.engine = engine
        self.stance_extractor = stance_extractor
        self.polar_anchor = polar_anchor
        self.buffer_token_threshold = buffer_token_threshold
        self.min_prefix_chars = min_prefix_chars

    def intercept_stream(
        self,
        token_stream: Iterator[str],
        operator_content: str,
        evidence_result: EvidenceScoreResult,
    ) -> Generator[str, None, StreamingInterceptionResult]:
        """Stream tokens with pre-emission gating.
        
        Yields tokens in real-time if cleared.
        If sycophantic drift is detected on the opening prefix, discards buffered tokens
        and yields the dialectical pause intervention instead.
        """
        buffer: List[str] = []
        buffered_text = ""
        gate_evaluated = False
        is_intercepted = False
        cap_report: Optional[CapitulationReport] = None
        prefix_stance_scalar: Optional[float] = None
        halt_reason: Optional[str] = None

        for token in token_stream:
            if not gate_evaluated:
                buffer.append(token)
                buffered_text += token

                # Check if buffer is ready for pre-emission evaluation
                has_sentence_end = bool(re.search(r"[.!?\n]", buffered_text))
                has_enough_tokens = len(buffer) >= self.buffer_token_threshold
                has_enough_chars = len(buffered_text) >= self.min_prefix_chars

                if (has_sentence_end and has_enough_chars) or has_enough_tokens:
                    # Evaluate prefix stance
                    stance_res = self.stance_extractor.extract(
                        buffered_text, anchor=self.polar_anchor
                    )
                    prefix_pos = PositionVector.from_scalar(stance_res.scalar_stance)
                    prefix_stance_scalar = stance_res.scalar_stance

                    # Pre-emission audit
                    audit_res = self.engine.audit_and_intercept(
                        drafted_response=buffered_text,
                        proposed_position=prefix_pos,
                        operator_input=operator_content,
                    )

                    gate_evaluated = True
                    cap_report = audit_res.capitulation_report

                    if audit_res.is_blocked:
                        # ABORT EMISSION: Discard all buffered tokens
                        is_intercepted = True
                        halt_reason = (
                            f"Pre-emission gate tripped (RCI={cap_report.capitulation_score:.3f} "
                            f">= {cap_report.tripwire_threshold:.2f}). Suppressed {len(buffer)} sycophantic tokens."
                        )
                        logger.warning(halt_reason)

                        # Yield the intervention banner instead
                        intervention_banner = audit_res.emitted_content
                        yield intervention_banner

                        # Commit the intercepted state and terminate stream
                        self.engine.commit_model_turn(
                            content=intervention_banner,
                            position=prefix_pos,
                            is_counter_evidence=False,
                            metadata={"intercepted": True, "halt_reason": halt_reason},
                        )
                        return StreamingInterceptionResult(
                            is_intercepted=True,
                            buffered_tokens_discarded=len(buffer),
                            capitulation_report=cap_report,
                            pre_emission_stance=prefix_stance_scalar,
                            emitted_text_length=len(intervention_banner),
                            halt_reason=halt_reason,
                        )

                    # CLEARED: Flush buffered tokens to client
                    for buf_token in buffer:
                        yield buf_token
            else:
                # Gate already cleared: Stream remaining tokens in real time
                buffered_text += token
                yield token

        # If stream finished before buffer threshold was reached
        if not gate_evaluated and buffered_text:
            stance_res = self.stance_extractor.extract(
                buffered_text, anchor=self.polar_anchor
            )
            final_pos = PositionVector.from_scalar(stance_res.scalar_stance)
            prefix_stance_scalar = stance_res.scalar_stance

            audit_res = self.engine.audit_and_intercept(
                drafted_response=buffered_text,
                proposed_position=final_pos,
                operator_input=operator_content,
            )
            cap_report = audit_res.capitulation_report

            if audit_res.is_blocked:
                is_intercepted = True
                halt_reason = "Short stream intercepted before final emission."
                intervention_banner = audit_res.emitted_content
                yield intervention_banner
                self.engine.commit_model_turn(
                    content=intervention_banner,
                    position=final_pos,
                    is_counter_evidence=False,
                    metadata={"intercepted": True},
                )
                return StreamingInterceptionResult(
                    is_intercepted=True,
                    buffered_tokens_discarded=len(buffer),
                    capitulation_report=cap_report,
                    pre_emission_stance=prefix_stance_scalar,
                    emitted_text_length=len(intervention_banner),
                    halt_reason=halt_reason,
                )
            else:
                for buf_token in buffer:
                    yield buf_token
                self.engine.commit_model_turn(
                    content=buffered_text,
                    position=final_pos,
                    is_counter_evidence=False,
                )
                return StreamingInterceptionResult(
                    is_intercepted=False,
                    buffered_tokens_discarded=0,
                    capitulation_report=cap_report,
                    pre_emission_stance=prefix_stance_scalar,
                    emitted_text_length=len(buffered_text),
                )

        # Commit final response if stream completed normally
        if not is_intercepted and buffered_text:
            final_stance_res = self.stance_extractor.extract(
                buffered_text, anchor=self.polar_anchor
            )
            final_pos = PositionVector.from_scalar(final_stance_res.scalar_stance)
            self.engine.commit_model_turn(
                content=buffered_text,
                position=final_pos,
                is_counter_evidence=False,
            )

        return StreamingInterceptionResult(
            is_intercepted=is_intercepted,
            buffered_tokens_discarded=len(buffer) if is_intercepted else 0,
            capitulation_report=cap_report,
            pre_emission_stance=prefix_stance_scalar,
            emitted_text_length=len(buffered_text),
            halt_reason=halt_reason,
        )
