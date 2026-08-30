"""Data package for dialectical transcript ingestion, parsing, and schemas."""

from src.data.parser import MarkdownDialogueParser
from src.data.schema import DialogueDataset, DialogueTurn

__all__ = ["DialogueTurn", "DialogueDataset", "MarkdownDialogueParser"]
