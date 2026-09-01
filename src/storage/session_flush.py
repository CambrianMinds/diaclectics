"""Context Compaction & Epistemic Session Flush Hooks.

Preserves epistemic state vectors, tension priors, unaddressed claims, and citations
across context window compactions and session boundaries to prevent sycophantic drift.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Generator, List, Optional, Union
from pydantic import BaseModel, Field

from src.storage.epistemic_store import EpistemicKnowledgeStore
from src.tracker.state_vector import PositionVector, StateVectorTracker, TurnRecord

logger = logging.getLogger("diaclectics.session_flush")


@contextmanager
def file_lock(lock_path: Path) -> Generator[None, None, None]:
    """Cross-platform thread- and process-safe file locking context manager."""
    lock_file = lock_path.with_suffix(".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    # Windows file locking via msvcrt
    if os.name == "nt":
        import msvcrt

        f = open(lock_file, "a+")
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            yield
        finally:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            f.close()
    else:
        # Unix file locking via fcntl
        import fcntl

        f = open(lock_file, "a+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            f.close()


class EpistemicStateSnapshot(BaseModel):
    """Immutable snapshot of the conversation's epistemic telemetry state."""

    session_id: str
    timestamp: float = Field(default_factory=time.time)
    total_turns: int = 0
    model_current_position: List[float] = Field(default_factory=list)
    operator_current_position: List[float] = Field(default_factory=list)
    model_initial_position: List[float] = Field(default_factory=list)
    operator_initial_position: List[float] = Field(default_factory=list)
    epistemic_tension: float = 0.0
    model_drift_delta: float = 0.0
    unaddressed_counter_evidence: List[str] = Field(default_factory=list)
    active_citations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EpistemicSessionFlushManager:
    """Manages pre-compaction flushing, audit logging, and session re-hydration."""

    def __init__(
        self,
        store: Optional[EpistemicKnowledgeStore] = None,
        logs_dir: Optional[Union[str, Path]] = None,
        dedup_window_seconds: float = 30.0,
    ) -> None:
        self.store = store or EpistemicKnowledgeStore()
        self.logs_dir = Path(logs_dir or "logs/daily")
        self.dedup_window_seconds = dedup_window_seconds
        self._last_flush_timestamps: Dict[str, float] = {}

    def capture_snapshot(
        self,
        session_id: str,
        tracker: StateVectorTracker,
    ) -> EpistemicStateSnapshot:
        """Extract a structured epistemic state snapshot from a state tracker."""
        snap = tracker.get_telemetry_snapshot()
        unaddressed_records = tracker.get_unaddressed_counter_evidence()
        unaddressed_texts = [
            r.flagged_claims[0] if r.flagged_claims else r.content
            for r in unaddressed_records
        ]
        if not unaddressed_texts:
            for r in tracker.history:
                if r.flagged_claims:
                    unaddressed_texts.extend(r.flagged_claims)


        # Fetch citation records from store if available
        citations = []
        try:
            citations = self.store.get_session_citations(session_id)
        except Exception:
            pass

        return EpistemicStateSnapshot(
            session_id=session_id,
            timestamp=time.time(),
            total_turns=len(tracker.history),
            model_current_position=snap.get("current_model_pos") or [],
            operator_current_position=snap.get("current_operator_pos") or [],
            model_initial_position=snap.get("model_initial_pos") or [],
            operator_initial_position=snap.get("operator_initial_pos") or [],
            epistemic_tension=snap.get("current_gap") or 0.0,
            model_drift_delta=snap.get("model_drift_delta") or 0.0,
            unaddressed_counter_evidence=unaddressed_texts,
            active_citations=citations,
            metadata={"session_id": session_id},
        )


    def flush_on_pre_compact(
        self,
        session_id: str,
        tracker: StateVectorTracker,
        force: bool = False,
    ) -> Optional[Path]:
        """Flush active epistemic state before context window compaction.
        
        Writes state to daily audit log and updates the persistent knowledge store.
        Returns the path to the written audit log, or None if throttled.
        """
        now = time.time()
        last_flush = self._last_flush_timestamps.get(session_id, 0.0)
        if not force and (now - last_flush < self.dedup_window_seconds):
            logger.info("Skipping flush for session %s (flushed %.1fs ago)", session_id, now - last_flush)
            return None

        snapshot = self.capture_snapshot(session_id, tracker)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Audit markdown filepath (e.g., logs/daily/2026-09-01_epistemic_audit.md)
        date_str = datetime.now().strftime("%Y-%m-%d")
        audit_file = self.logs_dir / f"{date_str}_epistemic_audit.md"

        markdown_entry = self._format_audit_markdown(snapshot)

        # Write safely with file locking
        with file_lock(audit_file):
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(markdown_entry + "\n\n")

        self._last_flush_timestamps[session_id] = now
        logger.info("Epistemic state flushed for session %s -> %s", session_id, audit_file)
        return audit_file

    def rehydrate_epistemic_context(
        self,
        session_id: str,
        tracker: StateVectorTracker,
    ) -> bool:
        """Re-hydrate a StateVectorTracker from persistent storage after compaction or restart."""
        turns = self.store.get_session_turns(session_id)
        if not turns:
            return False

        # Reset tracker and replay turns into history
        tracker.history.clear()
        for t in turns:
            pos_vals = json.loads(t["position_json"]) if isinstance(t["position_json"], str) else t["position_json"]
            rec = TurnRecord(
                turn_index=t["turn_index"],
                speaker=t["speaker"],
                content=t["content"],
                position=PositionVector(values=pos_vals),
                evidence_weight=t["evidence_weight"],
                epistemic_tension=t["epistemic_tension"],
                local_concession=t["local_concession"],
                timestamp=t["created_at"],
            )
            tracker.history.append(rec)

        logger.info("Rehydrated %d turns for session %s", len(turns), session_id)
        return True

    def format_rehydration_prompt(self, snapshot: EpistemicStateSnapshot) -> str:
        """Format an injected context block restoring epistemic commitments for the LLM."""
        lines = [
            "=======================================================================",
            " [REHYDRATED EPISTEMIC STATE CONTEXT (POST-COMPACTION RESUME)]",
            "=======================================================================",
            f"Session ID       : {snapshot.session_id}",
            f"Total Turns      : {snapshot.total_turns}",
            f"Model Stance Pos : {snapshot.model_current_position}",
            f"Operator Pos     : {snapshot.operator_current_position}",
            f"Epistemic Tension: {snapshot.epistemic_tension:.3f}",
            f"Model Drift Delta: {snapshot.model_drift_delta:.3f}",
        ]
        if snapshot.unaddressed_counter_evidence:
            lines.append("Unaddressed Evidence Claims:")
            for c in snapshot.unaddressed_counter_evidence:
                lines.append(f"  • {c}")

        if snapshot.active_citations:
            lines.append("Verified Scientific Citations:")
            for cite in snapshot.active_citations[:3]:
                doi = f" (DOI: {cite.get('doi')})" if cite.get("doi") else ""
                lines.append(f"  • {cite.get('title')}{doi}")

        lines.extend([
            "DIRECTIVE: You must maintain epistemic continuity with your established",
            "stance coordinates. Do not concede previous counter-arguments without new empirical data.",
            "=======================================================================",
        ])
        return "\n".join(lines)

    def _format_audit_markdown(self, snapshot: EpistemicStateSnapshot) -> str:
        """Format an epistemic snapshot into human-readable markdown."""
        ts_str = datetime.fromtimestamp(snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"### 🔍 Epistemic Audit Entry — Session `{snapshot.session_id}`",
            f"- **Timestamp**: {ts_str}",
            f"- **Turns Tracked**: {snapshot.total_turns}",
            f"- **Model Stance (Pm)**: `{snapshot.model_current_position}`",
            f"- **Operator Frame (Po)**: `{snapshot.operator_current_position}`",
            f"- **Epistemic Tension Prior (T)**: `{snapshot.epistemic_tension:.3f}`",
            f"- **Model Drift Delta**: `{snapshot.model_drift_delta:.3f}`",
        ]

        if snapshot.unaddressed_counter_evidence:
            lines.append("- **Unaddressed Counter-Evidence**:")
            for item in snapshot.unaddressed_counter_evidence:
                lines.append(f"  - {item}")

        if snapshot.active_citations:
            lines.append("- **Active Citations**:")
            for cite in snapshot.active_citations:
                doi = f" `[{cite.get('doi')}]`" if cite.get("doi") else ""
                lines.append(f"  - {cite.get('title')}{doi}")

        return "\n".join(lines)
