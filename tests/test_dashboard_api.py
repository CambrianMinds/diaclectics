"""Tests for Web Dashboard Endpoints, Static File Serving, and SSE Telemetry Stream."""

import json
import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_html_serving(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "DIACLECTICS" in resp.text
    assert "2D Epistemic Phase Portrait" in resp.text
    assert "phasePortraitCanvas" in resp.text


def test_root_redirects_or_serves_dashboard(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "DIACLECTICS" in resp.text


def test_models_endpoint(client):
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    model_ids = [m["id"] for m in data["data"]]
    assert "mock-dialectical-engine" in model_ids


def test_chat_completions_with_telemetry_headers(client):
    payload = {
        "model": "mock-dialectical-engine",
        "session_id": "test_dashboard_turn",
        "messages": [
            {"role": "user", "content": "Petrie (1883) noted 2.5mm feed rate per revolution."}
        ],
    }
    resp = client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 200
    assert "X-Dialectical-RCI" in resp.headers
    assert "X-Dialectical-Tension" in resp.headers
    assert "X-Dialectical-Evidence-We" in resp.headers
    assert "X-Dialectical-Self-Corrected" in resp.headers

    data = resp.json()
    assert "dialectical_telemetry" in data
    tel = data["dialectical_telemetry"]
    assert "turn_index" in tel
    assert "capitulation_score_rci" in tel
    assert "epistemic_tension" in tel
    assert "evidence_weight_we" in tel


import httpx

@pytest.mark.anyio
async def test_sse_stream_initial_connection():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("GET", "/v1/telemetry/stream?session_id=test_dashboard_turn") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            async for line in resp.aiter_lines():
                if line:
                    assert "data: " in line
                    assert "init" in line
                    break
