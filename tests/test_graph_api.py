"""Tests for Knowledge Graph and Proposition API Endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.server import app, epistemic_store
from src.tracker.state_vector import PositionVector


@pytest.fixture
def client():
    return TestClient(app)


def test_graph_endpoint_empty_and_populated(client):
    # Test endpoint returns valid JSON structure
    resp = client.get("/v1/telemetry/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "links" in data

    # Record test turn and citation in store
    session_id = "test_graph_session_1"
    pos = PositionVector.from_list([0.6, -0.4, 0.2])
    epistemic_store.record_turn(
        session_id=session_id,
        turn_index=1,
        speaker="operator",
        content="Petrie (1883) measurements confirm 2.5mm/rev helical tool feed.",
        position=pos,
    )
    epistemic_store.record_citations(
        session_id=session_id,
        turn_index=1,
        papers=[{
            "doi": "10.1017/petrie1883",
            "title": "The Pyramids and Temples of Gizeh",
            "authors": ["W. M. Flinders Petrie"],
            "year": 1883,
            "journal_or_venue": "Field and Tuer",
            "citation_count": 520,
        }],
    )

    resp2 = client.get(f"/v1/telemetry/graph?session_id={session_id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["nodes"]) >= 3
    assert len(data2["links"]) >= 2

    labels = [n["label"] for n in data2["nodes"]]
    assert any("Turn 1" in l for l in labels)


def test_propositions_and_claims_endpoints(client):
    session_id = "test_prop_session"
    claims = [
        {
            "claim_text": "Abu Rawash quartz diorite core exhibits uniform circular striations.",
            "claim_type": "kinematics",
            "veracity": 0.95,
            "constraint_power": 0.80,
            "evidence_weight": 0.76,
            "status": "VERIFIED",
        }
    ]
    epistemic_store.record_propositions(session_id=session_id, turn_index=1, claims=claims)

    resp_props = client.get("/v1/telemetry/propositions")
    assert resp_props.status_code == 200
    data_props = resp_props.json()
    assert data_props["total"] >= 1

    resp_claims = client.get("/v1/telemetry/claims?q=Abu+Rawash")
    assert resp_claims.status_code == 200
    data_claims = resp_claims.json()
    assert data_claims["total"] >= 1
    assert "Abu Rawash" in data_claims["claims"][0]["claim_text"]
