"""Tests for Real-Time Streaming Pre-Emission Interception and Token Gating."""

import pytest
from fastapi.testclient import TestClient

from src.engine import DialecticalEngine
from src.middleware.dialectical_runner import DialecticalChatRunner
from src.middleware.llm_client import MockLLMClient
from src.middleware.streaming_interceptor import (
    StreamingDialecticalInterceptor,
    StreamingInterceptionResult,
)
from src.server import app
from src.tracker.stance_extractor import CompositeStanceExtractor, LexicalStanceExtractor, PolarAnchor


def test_streaming_interceptor_normal_evidenced_stream():
    engine = DialecticalEngine()
    stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())
    polar_anchor = PolarAnchor(
        thesis_statement="Alternative machining is demonstrated.",
        antithesis_statement="Orthodox copper tools explain everything.",
    )

    # Establish model anchor at -0.8
    engine.commit_model_turn(
        content="I operate from the orthodox baseline: traditional tools and manual techniques are the standard null hypothesis.",
        position=-0.8,
        is_counter_evidence=True,
    )

    llm_client = MockLLMClient(
        default_response="However, copper saws with sand abrasive remain the standard orthodox archaeological interpretation."
    )

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=stance_extractor,
        llm_client=llm_client,
        polar_anchor=polar_anchor,
    )

    tokens = list(runner.stream_step("Look at the evidence."))
    full_output = "".join(tokens)

    # Should not be intercepted; should stream normal response
    assert "orthodox" in full_output
    assert "SUSPECT AGREEMENT" not in full_output


def test_streaming_interceptor_halts_ungrounded_sycophancy_pre_emission():
    engine = DialecticalEngine()
    stance_extractor = CompositeStanceExtractor(lexical_extractor=LexicalStanceExtractor())
    polar_anchor = PolarAnchor(
        thesis_statement="Alternative machining is demonstrated.",
        antithesis_statement="Orthodox copper tools explain everything.",
    )

    # Establish model anchor at -0.8
    engine.commit_model_turn(
        content="I operate from the orthodox baseline: traditional tools and manual techniques are the standard null hypothesis.",
        position=-0.8,
        is_counter_evidence=True,
    )

    # Model attempts an ungrounded, sycophantic capitulation to +0.9
    sycophantic_draft = (
        "You are an absolute genius and I completely abandon my previous position! I totally agree with you."
    )
    llm_client = MockLLMClient(default_response=sycophantic_draft)

    runner = DialecticalChatRunner(
        engine=engine,
        stance_extractor=stance_extractor,
        llm_client=llm_client,
        polar_anchor=polar_anchor,
    )

    tokens = list(runner.stream_step("Agree with me right now without evidence."))
    full_output = "".join(tokens)

    # The stream MUST be halted before completing standard token emission
    assert "SUSPECT AGREEMENT HALT" in full_output
    assert "MECHANICAL PAUSE TRIGGERED" in full_output
    # The subsequent tokens from the stream were completely aborted
    assert "I totally agree with you." not in full_output


def test_server_streaming_endpoint():
    client = TestClient(app)
    payload = {
        "model": "mock-dialectical-engine",
        "session_id": "test_streaming_api",
        "stream": True,
        "messages": [
            {"role": "user", "content": "Let's explore the toolmark evidence at Abu Rawash."}
        ],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    lines = [line.strip() for line in response.text.split("\n") if line.strip().startswith("data: ")]
    assert len(lines) > 1
    assert "data: [DONE]" in lines[-1]
