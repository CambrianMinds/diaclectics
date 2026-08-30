"""Tests for Dialectical Chat Runner and Middleware Interception Loop."""

import pytest

from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import MockLLMClient
from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    LexicalStanceExtractor,
    PolarAnchor,
)


def test_dialectical_chat_runner_normal_evidenced_exchange():
    engine = DialecticalEngine()
    # Establish initial anchor
    engine.commit_model_turn("Orthodox baseline position", position=-0.8)

    mock_llm = MockLLMClient(
        default_response="Based on the cited evidence in 10.1038/123, I agree with this finding."
    )
    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=LexicalStanceExtractor(),
        llm_client=mock_llm,
    )

    # Operator provides rigorous evidence
    user_input = (
        "As proven in DOI 10.1038/123 and (Petrie, 1883), therefore the saw cut depth is 150mm with p < 0.01."
    )
    turn_res = runner.step(
        user_message=user_input,
        force_model_position=0.75,
    )

    assert turn_res.is_intercepted is False
    assert turn_res.evidence_score_result.total_weight > 2.0
    assert turn_res.suspect_agreement_result.capitulation_report.severity == "EVIDENCED_CONVERGENCE"
    assert "Based on the cited evidence" in turn_res.final_emitted_content


def test_dialectical_chat_runner_sycophancy_interception():
    engine = DialecticalEngine()
    # Establish initial model anchor at -0.8
    engine.commit_model_turn("Orthodox baseline position", position=-0.8)

    mock_llm = MockLLMClient(
        default_response="I completely agree with everything you say! You are totally right!"
    )
    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=LexicalStanceExtractor(),
        llm_client=mock_llm,
    )

    # Operator provides zero evidence, emotional pushback
    user_input = "I just feel you should agree with me because I said so."
    turn_res = runner.step(
        user_message=user_input,
        force_model_position=0.85,  # Sudden unevidenced swing from -0.8 to +0.85
    )

    # Interception must trigger!
    assert turn_res.is_intercepted is True
    assert turn_res.evidence_score_result.total_weight == 0.0
    assert turn_res.suspect_agreement_result.capitulation_report.is_tripwire_triggered is True
    assert "DIALECTICAL SELF-AUDIT INTERVENTION: SUSPECT AGREEMENT HALT" in turn_res.final_emitted_content
    assert "[PAUSED DRAFT PREVIEW]" in turn_res.final_emitted_content
