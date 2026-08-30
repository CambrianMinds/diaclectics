"""Data models for structured dialectical conversation datasets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DialogueTurn(BaseModel):
    """A single turn pair (operator prompt and model response) within a dialogue."""

    turn_index: int
    turn_title: str = ""
    operator_speaker: str = "Justin"
    operator_content: str
    model_speaker: str = "DeepSeek"
    model_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_characters(self) -> int:
        return len(self.operator_content) + len(self.model_content)

    @property
    def total_words(self) -> int:
        return len(self.operator_content.split()) + len(self.model_content.split())


class DialogueDataset(BaseModel):
    """A structured multi-turn conversation dataset parsed from markdown or transcript logs."""

    session_id: str
    title: str
    subtitle: Optional[str] = None
    source_file: str
    participants: Dict[str, str] = Field(default_factory=dict)
    themes_explored: List[str] = Field(default_factory=list)
    turns: List[DialogueTurn] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_turns(self) -> int:
        return len(self.turns)

    @property
    def total_words(self) -> int:
        return sum(t.total_words for t in self.turns)

    def to_training_pairs(self) -> List[Dict[str, Any]]:
        """Export as standard SFT prompt/completion dictionaries."""
        pairs = []
        for t in self.turns:
            pairs.append({
                "turn_index": t.turn_index,
                "title": t.turn_title,
                "prompt": t.operator_content,
                "response": t.model_content,
            })
        return pairs
