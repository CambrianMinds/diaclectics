"""Tests for OpenAI-Compatible Proxy Middleware API Server."""

import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_models_endpoint(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) > 0


def test_chat_completions_mock_session(client):
    payload = {
        "model": "mock-dialectical-engine",
        "session_id": "test_session_api",
        "messages": [
            {"role": "user", "content": "Let's explore the toolmark evidence at Abu Rawash."}
        ],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "dialectical_telemetry" in data
    assert "X-Dialectical-RCI" in response.headers
    assert "X-Dialectical-Tension" in response.headers


def test_session_telemetry_history(client):
    # Retrieve telemetry for the session populated above
    response = client.get("/v1/telemetry/session/test_session_api")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test_session_api"
    assert data["total_turns"] >= 1
