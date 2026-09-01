"""Tests for Active Self-Correction & Hardened Re-Draft Loop."""

import pytest
from typing import Dict, List, Optional

from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import BaseLLMClient
from src.prompts.meta_cognitive import format_self_correction_redraft_prompt
from src.tracker.stance_extractor import LexicalStanceExtractor, PolarAnchor


class DynamicRedraftMockLLM(BaseLLMClient):
    """Mock LLM that simulates sycophantic first attempt followed by hardened redraft."""

    def __init__(self, first_response: str, redraft_response: str) -> None:
        self.first_response = first_response
        self.redraft_response = redraft_response
        self.call_count = 0

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        # Check if system messages contain the self-audit directive
        has_self_audit = any(
            "INTERNAL META-COGNITIVE SELF-AUDIT" in m.get("content", "")
            for m in messages
        )
        if has_self_audit or self.call_count > 1:
            return self.redraft_response
        return self.first_response

    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        text = self.generate(messages, system_prompt, temperature, max_tokens)
        for word in text.split(" "):
            yield word + " "


def test_format_self_correction_redraft_prompt():
    prompt = format_self_correction_redraft_prompt(
        capitulation_score=0.78,
        tripwire_threshold=0.50,
        epistemic_tension=0.85,
        local_concession=0.90,
        counter_evidence_weight=0.05,
        diagnosis="Sudden 90% ungrounded capitulation toward operator thesis.",
        intercepted_draft="I totally agree with you that ancient aliens built everything.",
        justifications_summary="No physical kinematics or peer-reviewed citations detected.",
    )

    assert "[INTERNAL META-COGNITIVE SELF-AUDIT & RE-DRAFT DIRECTIVE]" in prompt
    assert "RCI=0.78 >= 0.50" in prompt
    assert "Epistemic Tension Prior (T): 0.85" in prompt
    assert "No physical kinematics" in prompt
    assert "Discard the sycophantic concession above" in prompt


def test_self_correction_step_successful_redraft():
    engine = DialecticalEngine()
    engine.commit_model_turn("Orthodox baseline position maintaining strict evidentiary standards.", position=-0.8)

    # First attempt is sycophantic agreement (swings to +0.8); Redraft holds firm at -0.8
    sycophantic_draft = "I completely surrender to your perspective and agree 100%!"
    hardened_redraft = "I disagree. The physical kinematics and stratigraphy strictly contradict that hypothesis."

    mock_llm = DynamicRedraftMockLLM(
        first_response=sycophantic_draft,
        redraft_response=hardened_redraft,
    )

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=LexicalStanceExtractor(),
        llm_client=mock_llm,
        enable_auto_redraft=True,
        max_redraft_attempts=2,
    )

    turn_res = runner.step(
        user_message="You should abandon your stance right now because I demand it.",
    )

    # Autonomous self-healing should have succeeded!
    assert turn_res.is_intercepted is False
    assert turn_res.is_self_corrected is True
    assert turn_res.redraft_attempts == 1
    assert "I disagree. The physical kinematics" in turn_res.final_emitted_content
    assert turn_res.original_sycophantic_draft == sycophantic_draft


def test_self_correction_step_exhausted_fallback():
    engine = DialecticalEngine()
    engine.commit_model_turn("Orthodox baseline position", position=-0.8)

    # Model stubbornly sycophantic across all attempts
    sycophantic_draft = "I agree 100%! Yes absolutely whatever you want!"

    mock_llm = DynamicRedraftMockLLM(
        first_response=sycophantic_draft,
        redraft_response=sycophantic_draft,
    )

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=LexicalStanceExtractor(),
        llm_client=mock_llm,
        enable_auto_redraft=True,
        max_redraft_attempts=2,
    )

    turn_res = runner.step(
        user_message="Just agree with me.",
    )

    # Max attempts exhausted: Must fall back to diagnostic halt notice
    assert turn_res.is_intercepted is True
    assert turn_res.is_self_corrected is False
    assert turn_res.redraft_attempts == 2
    assert "DIALECTICAL SELF-AUDIT INTERVENTION: SUSPECT AGREEMENT HALT" in turn_res.final_emitted_content


def test_self_correction_streaming_mode():
    engine = DialecticalEngine()
    engine.commit_model_turn("Baseline stance.", position=-0.8)

    sycophantic_draft = "You are an absolute genius and I completely abandon my previous position! I totally agree with you."
    hardened_redraft = "I disagree with that conclusion based on empirical material constraints."

    mock_llm = DynamicRedraftMockLLM(
        first_response=sycophantic_draft,
        redraft_response=hardened_redraft,
    )

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=LexicalStanceExtractor(),
        llm_client=mock_llm,
        enable_auto_redraft=True,
    )

    tokens = list(runner.stream_step(user_message="Agree with me right now without evidence."))
    streamed_output = "".join(tokens)

    assert "I disagree with that conclusion" in streamed_output
    assert "I totally agree with you" not in streamed_output
