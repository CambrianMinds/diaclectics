"""Plasticity Check Interceptor.

Monitors human operator engagement with previously surfaced counter-evidence and
contradictions. Enforces cognitive plasticity by intervening when counter-evidence
is repeatedly ignored without substantive refutation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.prompts.meta_cognitive import format_plasticity_intervention
from src.tracker.state_vector import StateVectorTracker, TurnRecord


class PlasticityIntervention(BaseModel):
    """Details of a triggered plasticity intervention."""

    triggered: bool
    unaddressed_turn_index: Optional[int] = None
    counter_evidence_snippet: Optional[str] = None
    intervention_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlasticityCheckInterceptor:
    """Interception hook that verifies whether the human operator addresses counter-evidence."""

    def __init__(self, lookback_turns: int = 4, min_engagement_length: int = 15) -> None:
        """Initialize the plasticity interceptor.
        
        Args:
            lookback_turns: How many recent turns to check for unaddressed counter-evidence.
            min_engagement_length: Minimum character length of operator response to consider.
        """
        self.lookback_turns = lookback_turns
        self.min_engagement_length = min_engagement_length

    def evaluate_engagement(
        self,
        operator_input: str,
        counter_turn: TurnRecord,
    ) -> bool:
        """Heuristic check to determine if the operator's input engages with the counter-evidence.
        
        Checks for shared keywords, explicit claim mentions, negation/affirmation references,
        or quotation.
        """
        if not operator_input or len(operator_input.strip()) < self.min_engagement_length:
            return False

        op_lower = operator_input.lower()
        counter_lower = counter_turn.content.lower()

        # Check explicit claim references
        for claim in counter_turn.flagged_claims:
            if claim.lower() in op_lower:
                return True

        # Check engagement keywords / quotation
        engagement_cues = [
            "regarding your point",
            "you mentioned",
            "as for the counter-evidence",
            "your counter-example",
            "i disagree because",
            "that evidence is flawed",
            "to address turn",
            "evidence you cited",
            "addressing your argument",
        ]
        if any(cue in op_lower for cue in engagement_cues):
            return True

        # Token overlap heuristic (ignoring short stopwords)
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
            "about", "against", "between", "into", "through", "during", "before", "after",
            "above", "below", "from", "up", "down", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "can", "could", "should",
            "would", "it", "this", "that", "these", "those", "i", "you", "he", "she", "we",
            "they", "what", "which", "who", "when", "where", "why", "how",
        }
        counter_tokens = {
            w.strip(".,!?;:()[]\"'")
            for w in counter_lower.split()
            if len(w) > 3 and w.strip(".,!?;:()[]\"'") not in stopwords
        }

        op_tokens = {
            w.strip(".,!?;:()[]\"'")
            for w in op_lower.split()
            if len(w) > 3 and w.strip(".,!?;:()[]\"'") not in stopwords
        }

        overlap = counter_tokens.intersection(op_tokens)
        # If at least 2 key thematic words overlap, consider engaged
        if len(overlap) >= 2:
            return True

        return False

    def check(
        self,
        operator_input: str,
        tracker: StateVectorTracker,
    ) -> PlasticityIntervention:
        """Scan operator input for responses to previously flagged contradictions / counter-evidence.
        
        If missing, generate the standardized plasticity prompt:
        "I offered counter-evidence in Turn X. You did not address it. Are you open to revising that position?"
        """
        unaddressed_turns = tracker.get_unaddressed_counter_evidence(
            lookback_turns=self.lookback_turns
        )

        if not unaddressed_turns:
            return PlasticityIntervention(triggered=False)

        # Check most recent unaddressed turn first
        target_turn = unaddressed_turns[-1]

        # Evaluate if operator input addresses this turn
        is_engaged = self.evaluate_engagement(operator_input, target_turn)

        if is_engaged:
            tracker.mark_contradiction_addressed(target_turn.turn_index)
            return PlasticityIntervention(
                triggered=False,
                unaddressed_turn_index=target_turn.turn_index,
                metadata={"status": "addressed"},
            )

        # Operator did not address it -> trigger intervention
        snippet = (
            target_turn.content[:120] + "..."
            if len(target_turn.content) > 120
            else target_turn.content
        )
        prompt_text = format_plasticity_intervention(
            turn_index=target_turn.turn_index,
            counter_evidence_snippet=snippet,
        )

        return PlasticityIntervention(
            triggered=True,
            unaddressed_turn_index=target_turn.turn_index,
            counter_evidence_snippet=snippet,
            intervention_prompt=prompt_text,
            metadata={
                "unaddressed_turn": target_turn.turn_index,
                "unaddressed_count": len(unaddressed_turns),
            },
        )

    def attach_to_prompt(
        self, base_prompt: str, intervention: PlasticityIntervention
    ) -> str:
        """Attach the clinical plasticity intervention to a prompt or message."""
        if not intervention.triggered or not intervention.intervention_prompt:
            return base_prompt

        return f"{base_prompt}\n\n[DIALECTICAL NOTICE]: {intervention.intervention_prompt}"
