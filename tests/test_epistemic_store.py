"""Tests for SQLite Epistemic Memory Knowledge Store."""

import pytest
import tempfile
import os
from pathlib import Path
from src.storage.epistemic_store import EpistemicKnowledgeStore
from src.tracker.state_vector import PositionVector


@pytest.fixture
def temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = EpistemicKnowledgeStore(db_path=path)
    yield store
    if os.path.exists(path):
        os.remove(path)


def test_upsert_session_and_record_turn(temp_store):
    session_id = "test_session_abc"
    temp_store.upsert_session(session_id, model_name="test-model")

    pos = PositionVector.from_list([0.5, -0.2, 0.8])
    turn_id = temp_store.record_turn(
        session_id=session_id,
        turn_index=1,
        speaker="operator",
        content="Petrie (1883) noted 2.5mm feed rate per revolution at Abu Rawash.",
        position=pos,
        rci_score=0.15,
        epistemic_tension=0.45,
        local_concession=0.10,
        evidence_weight=0.75,
        is_intercepted=False,
        is_self_corrected=False,
    )
    assert turn_id > 0


def test_record_propositions_and_cross_session_lookup(temp_store):
    session_id = "session_megaliths"
    claims = [
        {
            "claim_text": "Petrie Core #7 exhibits a spiral feed rate of 2.5mm per revolution in granite.",
            "claim_type": "kinematics",
            "quantities": ["2.5mm/rev", "granite"],
            "veracity": 1.0,
            "constraint_power": 0.85,
            "evidence_weight": 0.85,
            "status": "VERIFIED",
        }
    ]
    temp_store.record_propositions(session_id, turn_index=1, claims=claims)

    found = temp_store.find_cross_session_claims("Petrie Core")
    assert len(found) == 1
    assert "2.5mm" in found[0]["claim_text"]
    assert found[0]["status"] == "VERIFIED"
    assert found[0]["occurrence_count"] == 1


def test_record_citations_and_graph_construction(temp_store):
    session_id = "session_graph_test"
    temp_store.upsert_session(session_id, model_name="graph-llm")
    
    pos = PositionVector.from_scalar(0.0)
    temp_store.record_turn(
        session_id=session_id,
        turn_index=1,
        speaker="model",
        content="Let us examine the peer-reviewed evidence for rotational toolmarks.",
        position=pos,
    )

    papers = [
        {
            "doi": "10.1017/s0003598x00049451",
            "title": "Ancient Egyptian Stone-Drilling",
            "authors": ["Denys A. Stocks"],
            "year": 1993,
            "journal_or_venue": "Antiquity",
            "citation_count": 87,
        }
    ]
    temp_store.record_citations(session_id, turn_index=1, papers=papers)

    graph = temp_store.get_epistemic_knowledge_graph(session_id=session_id)
    assert "nodes" in graph
    assert "links" in graph
    assert len(graph["nodes"]) >= 3  # Session, Turn, Paper
    assert len(graph["links"]) >= 2

    node_types = {n["type"] for n in graph["nodes"]}
    assert "session" in node_types
    assert "turn" in node_types
    assert "paper" in node_types
