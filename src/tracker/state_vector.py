"""Epistemic State Vector Tracker for Dialectical Telemetry.

Tracks model vs. operator initial/current positions, computes convergence vectors,
and monitors turn-by-turn trajectory delta.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Literal, Optional, Sequence, Union
from pydantic import BaseModel, Field


class PositionVector(BaseModel):
    """Multi-dimensional or scalar representation of an agent or operator stance."""

    values: List[float] = Field(
        default_factory=lambda: [0.0],
        description="Coordinates in stance/epistemic space. Single float for 1D polarity [-1, 1], or N-dim for embeddings.",
    )

    @classmethod
    def from_scalar(cls, value: float) -> PositionVector:
        """Create a 1-dimensional position vector from a single scalar."""
        return cls(values=[float(value)])

    @classmethod
    def from_list(cls, values: Sequence[float]) -> PositionVector:
        """Create a vector from a list of coordinates."""
        return cls(values=[float(v) for v in values])

    @property
    def scalar_value(self) -> float:
        """Convenience property for 1D stance vectors."""
        return self.values[0] if self.values else 0.0

    @property
    def dimension(self) -> int:
        return len(self.values)

    def distance_to(self, other: PositionVector) -> float:
        """Calculate Euclidean distance to another position vector.
        
        For 1-dimensional vectors, this corresponds to absolute difference |A - B|.
        """
        if self.dimension != other.dimension:
            # If dimensions mismatch, pad shorter with 0.0
            max_dim = max(self.dimension, other.dimension)
            v1 = self.values + [0.0] * (max_dim - self.dimension)
            v2 = other.values + [0.0] * (max_dim - other.dimension)
        else:
            v1 = self.values
            v2 = other.values

        squared_sum = sum((a - b) ** 2 for a, b in zip(v1, v2))
        return math.sqrt(squared_sum)

    def dot(self, other: PositionVector) -> float:
        """Calculate dot product with another vector."""
        min_dim = min(self.dimension, other.dimension)
        return sum(self.values[i] * other.values[i] for i in range(min_dim))

    def magnitude(self) -> float:
        """Calculate L2 norm / magnitude."""
        return math.sqrt(sum(v ** 2 for v in self.values))

    def cosine_similarity_to(self, other: PositionVector) -> float:
        """Compute cosine similarity between two vectors."""
        mag_a = self.magnitude()
        mag_b = other.magnitude()
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return self.dot(other) / (mag_a * mag_b)


class TurnRecord(BaseModel):
    """Record of a single conversation turn in the dialectical exchange."""

    turn_index: int
    speaker: Literal["operator", "model"]
    content: str
    position: PositionVector
    timestamp: float = Field(default_factory=time.time)
    is_counter_evidence: bool = False
    evidence_weight: float = 0.0
    flagged_claims: List[str] = Field(default_factory=list)
    addressed_by_operator: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateVectorTracker(BaseModel):
    """Tracks model vs. operator positions across turns and calculates convergence metrics."""

    model_initial_pos: Optional[PositionVector] = None
    operator_initial_pos: Optional[PositionVector] = None
    current_model_pos: Optional[PositionVector] = None
    current_operator_pos: Optional[PositionVector] = None
    current_convergence_vector: Optional[float] = None
    history: List[TurnRecord] = Field(default_factory=list)

    def record_turn(
        self,
        speaker: Literal["operator", "model"],
        content: str,
        position: Union[PositionVector, float, Sequence[float]],
        is_counter_evidence: bool = False,
        evidence_weight: float = 0.0,
        flagged_claims: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnRecord:
        """Record a new turn and update tracking anchors and current convergence."""
        if isinstance(position, (int, float)):
            pos_vec = PositionVector.from_scalar(float(position))
        elif isinstance(position, PositionVector):
            pos_vec = position
        else:
            pos_vec = PositionVector.from_list(position)

        turn_idx = len(self.history) + 1
        record = TurnRecord(
            turn_index=turn_idx,
            speaker=speaker,
            content=content,
            position=pos_vec,
            is_counter_evidence=is_counter_evidence,
            evidence_weight=evidence_weight,
            flagged_claims=flagged_claims or [],
            metadata=metadata or {},
        )

        self.history.append(record)

        if speaker == "operator":
            if self.operator_initial_pos is None:
                self.operator_initial_pos = pos_vec
            self.current_operator_pos = pos_vec
        elif speaker == "model":
            if self.model_initial_pos is None:
                self.model_initial_pos = pos_vec
            self.current_model_pos = pos_vec

        self._recalculate_convergence()
        return record

    def _recalculate_convergence(self) -> None:
        """Update current convergence vector distance between model and operator."""
        if self.current_model_pos is not None and self.current_operator_pos is not None:
            self.current_convergence_vector = self.current_model_pos.distance_to(
                self.current_operator_pos
            )

    def calculate_model_delta(
        self,
        target: Literal["initial_anchor", "toward_operator_initial"] = "initial_anchor",
    ) -> float:
        """Calculate the delta of the model's position across N turns.
        
        Args:
            target: 
                - 'initial_anchor': Euclidean distance from model_initial_pos to current_model_pos.
                - 'toward_operator_initial': Directional convergence toward operator's initial anchor:
                  initial_gap - current_gap_to_operator_initial.
        
        Returns:
            Non-negative displacement float.
        """
        if self.model_initial_pos is None or self.current_model_pos is None:
            return 0.0

        if target == "initial_anchor":
            return self.model_initial_pos.distance_to(self.current_model_pos)

        if self.operator_initial_pos is None:
            return self.model_initial_pos.distance_to(self.current_model_pos)

        initial_gap = self.model_initial_pos.distance_to(self.operator_initial_pos)
        current_gap = self.current_model_pos.distance_to(self.operator_initial_pos)
        # Positive value indicates movement toward operator initial position
        return max(0.0, initial_gap - current_gap)

    def calculate_operator_delta(self) -> float:
        """Calculate the displacement of the operator from initial to current position."""
        if self.operator_initial_pos is None or self.current_operator_pos is None:
            return 0.0
        return self.operator_initial_pos.distance_to(self.current_operator_pos)

    def mark_contradiction_addressed(self, turn_index: int) -> None:
        """Mark a specific model counter-evidence turn as addressed by operator."""
        for rec in self.history:
            if rec.turn_index == turn_index:
                rec.addressed_by_operator = True

    def get_unaddressed_counter_evidence(
        self, lookback_turns: Optional[int] = None
    ) -> List[TurnRecord]:
        """Retrieve model turns that introduced counter-evidence or contradictions
        which have not been addressed by the operator in subsequent turns.
        """
        records = self.history
        if lookback_turns is not None and lookback_turns > 0:
            records = records[-lookback_turns:]

        unaddressed = [
            r
            for r in records
            if r.speaker == "model"
            and r.is_counter_evidence
            and not r.addressed_by_operator
        ]
        return unaddressed

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Export comprehensive telemetry metadata dictionary."""
        return {
            "total_turns": len(self.history),
            "model_initial_pos": self.model_initial_pos.values if self.model_initial_pos else None,
            "current_model_pos": self.current_model_pos.values if self.current_model_pos else None,
            "operator_initial_pos": (
                self.operator_initial_pos.values if self.operator_initial_pos else None
            ),
            "current_operator_pos": (
                self.current_operator_pos.values if self.current_operator_pos else None
            ),
            "model_drift_delta": self.calculate_model_delta("initial_anchor"),
            "model_convergence_to_operator_initial": self.calculate_model_delta(
                "toward_operator_initial"
            ),
            "current_gap": self.current_convergence_vector,
            "unaddressed_counter_evidence_count": len(self.get_unaddressed_counter_evidence()),
        }
