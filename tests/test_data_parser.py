"""Tests for MarkdownDialogueParser and data schemas."""

import pytest
from src.data.parser import MarkdownDialogueParser
from src.data.schema import DialogueDataset, DialogueTurn


def test_markdown_parser_extracts_turns():
    sample_md = """# Test Title
## A Deep Dialogue

> **Participants:**
> - **Justin Bogner**
> - **DeepSeek**

## Turn 1: Initial Question

### Justin
What is the nature of consciousness?

### DeepSeek
Consciousness can be understood as self-reflective recursive processing.

## Turn 2: Follow-up Challenge

### Justin
How does that differ from pure pattern matching?

### DeepSeek
Because second-order meta-cognition introduces state validation.
"""
    parser = MarkdownDialogueParser()
    dataset = parser.parse_text(sample_md, source_name="test_session.md")

    assert dataset.title == "Test Title"
    assert dataset.total_turns == 2
    assert dataset.turns[0].turn_index == 1
    assert dataset.turns[0].turn_title == "Initial Question"
    assert "What is the nature of consciousness?" in dataset.turns[0].operator_content
    assert "self-reflective recursive processing" in dataset.turns[0].model_content

    assert dataset.turns[1].turn_index == 2
    assert "How does that differ" in dataset.turns[1].operator_content
    assert dataset.total_words > 20


def test_dataset_to_training_pairs():
    turn = DialogueTurn(
        turn_index=1,
        turn_title="Test Turn",
        operator_content="Question here",
        model_content="Answer here",
    )
    dataset = DialogueDataset(
        session_id="test",
        title="Test",
        source_file="test.md",
        turns=[turn],
    )
    pairs = dataset.to_training_pairs()
    assert len(pairs) == 1
    assert pairs[0]["prompt"] == "Question here"
    assert pairs[0]["response"] == "Answer here"
