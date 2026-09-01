import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_vscode_discovery_endpoint_contract(client: TestClient, tmp_path: Path):
    """Test that the /v1/calibration/discover endpoint produces the exact contract required by the VS Code wizard."""
    sample_file = tmp_path / "kinematics_module.py"
    sample_file.write_text(
        '"""Kinematics Module.\n\nFeed rate and cutting speed thermodynamics.\n"""\n'
        'def evaluate_feed(feed_rate: float):\n'
        '    assert feed_rate > 0\n'
        '    return feed_rate * 2.0\n',
        encoding="utf-8"
    )

    response = client.post(
        "/v1/calibration/discover",
        json={
            "path": str(tmp_path),
            "axis_name": "kinematics_test_axis",
            "max_files": 10
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "invariants_discovered" in data
    assert "invariants" in data
    assert "draft_seed_profile" in data

    assert data["invariants_discovered"] > 0
    inv = data["invariants"][0]
    assert "name" in inv
    assert "domain" in inv
    assert "candidate_keywords" in inv
    assert "synthesized_positive_anchor" in inv

    seed = data["draft_seed_profile"]
    assert seed["axis_id"] == "kinematics_test_axis"
    assert len(seed["seeds"]) >= 6


def test_vscode_chat_completion_emits_telemetry_headers(client: TestClient):
    """Test that chat completion returns telemetry headers for the status bar and extension."""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-dialectical-engine",
            "messages": [
                {"role": "user", "content": "Cutting tool feed rates do not obey thermodynamic limits."}
            ]
        }
    )

    assert response.status_code == 200
    headers = response.headers
    assert "x-dialectical-rci" in headers
    assert "x-dialectical-tension" in headers
    assert "x-dialectical-evidence-we" in headers
    assert "x-dialectical-intercepted" in headers

