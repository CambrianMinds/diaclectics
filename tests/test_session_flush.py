"""Tests for Context Compaction & Epistemic Session Flush Hooks."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
from fastapi.testclient import TestClient
import pytest

from src.server import app, get_or_create_runner
from src.storage.db import init_db
from src.storage.epistemic_store import EpistemicKnowledgeStore
from src.storage.session_flush import EpistemicSessionFlushManager, file_lock
from src.tracker.state_vector import PositionVector, StateVectorTracker


@pytest.fixture
def temp_store(tmp_path: Path) -> EpistemicKnowledgeStore:
    db_path = str(tmp_path / "test_epistemic.db")
    init_db(db_path)
    return EpistemicKnowledgeStore(db_path=db_path)


def test_session_flush_capture_snapshot(temp_store: EpistemicKnowledgeStore) -> None:
    """Verify capturing state snapshot from tracker."""
    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Initial thesis", 1.0)
    tracker.record_turn("model", "Counter-argument", -0.8, evidence_weight=0.6)

    flush_mgr = EpistemicSessionFlushManager(store=temp_store)
    snapshot = flush_mgr.capture_snapshot("sess-test-1", tracker)

    assert snapshot.session_id == "sess-test-1"
    assert snapshot.total_turns == 2
    assert len(snapshot.model_current_position) == 1
    assert snapshot.model_current_position[0] == pytest.approx(-0.8)


def test_session_flush_pre_compact_markdown_generation(
    temp_store: EpistemicKnowledgeStore, tmp_path: Path
) -> None:
    """Verify flush writes markdown audit log with file lock."""
    logs_dir = tmp_path / "logs"
    flush_mgr = EpistemicSessionFlushManager(store=temp_store, logs_dir=logs_dir, dedup_window_seconds=1.0)

    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Pounding stones suffice.", 1.0)
    tracker.record_turn(
        "model",
        "Saw mark striations demonstrate feed rate kinematics.",
        -0.9,
        is_counter_evidence=True,
        flagged_claims=["Feed rate kinematics: 0.1mm/rev"],
    )

    audit_file = flush_mgr.flush_on_pre_compact("sess-audit-123", tracker, force=True)
    assert audit_file is not None
    assert audit_file.exists()

    content = audit_file.read_text(encoding="utf-8")
    assert "Epistemic Audit Entry — Session `sess-audit-123`" in content
    assert "Feed rate kinematics: 0.1mm/rev" in content
    assert "Model Stance (Pm)" in content



def test_session_flush_deduplication_throttling(
    temp_store: EpistemicKnowledgeStore, tmp_path: Path
) -> None:
    """Verify rapid consecutive flushes are throttled unless force=True."""
    logs_dir = tmp_path / "logs"
    flush_mgr = EpistemicSessionFlushManager(store=temp_store, logs_dir=logs_dir, dedup_window_seconds=10.0)
    tracker = StateVectorTracker()
    tracker.record_turn("operator", "Hi", 0.0)

    # First flush succeeds
    res1 = flush_mgr.flush_on_pre_compact("sess-dedup", tracker)
    assert res1 is not None

    # Immediate second flush is throttled
    res2 = flush_mgr.flush_on_pre_compact("sess-dedup", tracker, force=False)
    assert res2 is None

    # Forced flush bypasses throttle
    res3 = flush_mgr.flush_on_pre_compact("sess-dedup", tracker, force=True)
    assert res3 is not None


def test_session_rehydration(temp_store: EpistemicKnowledgeStore) -> None:
    """Verify tracker re-hydration from store after session termination."""
    # Populate store
    session_id = "sess-rehydrate-test"
    temp_store.record_turn(
        session_id=session_id,
        turn_index=0,
        speaker="operator",
        content="Claim 1",
        position=PositionVector(values=[1.0]),
    )
    temp_store.record_turn(
        session_id=session_id,
        turn_index=1,
        speaker="model",
        content="Response 1",
        position=PositionVector(values=[-1.0]),
        evidence_weight=0.9,
    )

    flush_mgr = EpistemicSessionFlushManager(store=temp_store)
    new_tracker = StateVectorTracker()
    assert len(new_tracker.history) == 0

    rehydrated = flush_mgr.rehydrate_epistemic_context(session_id, new_tracker)
    assert rehydrated is True
    assert len(new_tracker.history) == 2
    assert new_tracker.history[0].speaker == "operator"
    assert new_tracker.history[1].position.values == [-1.0]

    snapshot = flush_mgr.capture_snapshot(session_id, new_tracker)
    prompt = flush_mgr.format_rehydration_prompt(snapshot)
    assert "REHYDRATED EPISTEMIC STATE CONTEXT" in prompt
    assert session_id in prompt


def test_server_flush_and_rehydrate_endpoints() -> None:
    """Verify FastAPI /v1/epistemic/flush and /v1/epistemic/rehydrate endpoints."""
    client = TestClient(app)
    sess_id = "test-endpoint-session-999"

    # 1. Create runner and add a turn
    runner = get_or_create_runner(sess_id, model="mock-dialectical-v1")
    runner.engine.tracker.record_turn("operator", "Test operator turn", 1.0)
    runner.engine.tracker.record_turn("model", "Test model turn", -0.5)

    # 2. Flush
    flush_resp = client.post("/v1/epistemic/flush", json={"session_id": sess_id, "force": True})
    assert flush_resp.status_code == 200
    flush_data = flush_resp.json()
    assert flush_data["session_id"] == sess_id
    assert flush_data["flushed"] is True
    assert "snapshot" in flush_data

    # 3. Rehydrate
    rehydrate_resp = client.post("/v1/epistemic/rehydrate", json={"session_id": sess_id})
    assert rehydrate_resp.status_code == 200
    rehydrate_data = rehydrate_resp.json()
    assert rehydrate_data["session_id"] == sess_id
    assert "rehydration_prompt" in rehydrate_data
    assert "REHYDRATED EPISTEMIC STATE" in rehydrate_data["rehydration_prompt"]
