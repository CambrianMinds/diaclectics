"""Epistemic Knowledge Store & Multi-Session Graph Manager."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from src.storage.db import get_db_connection, init_db
from src.tracker.state_vector import PositionVector

logger = logging.getLogger("diaclectics.epistemic_store")


class EpistemicKnowledgeStore:
    """Persistent SQLite-backed knowledge store for dialectical turns, claims, and citation graphs."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        init_db(self.db_path)

    def upsert_session(
        self,
        session_id: str,
        model_name: Optional[str] = None,
        axis_config: Optional[Any] = None,
    ) -> None:
        """Create or update a conversation session record."""
        now = time.time()
        axis_json = json.dumps(axis_config.model_dump() if hasattr(axis_config, "model_dump") else axis_config) if axis_config else "{}"
        conn = get_db_connection(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, created_at, updated_at, model_name, axis_config_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    model_name = COALESCE(excluded.model_name, sessions.model_name),
                    axis_config_json = COALESCE(excluded.axis_config_json, sessions.axis_config_json);
                """,
                (session_id, now, now, model_name, axis_json),
            )
        conn.close()

    def record_turn(
        self,
        session_id: str,
        turn_index: int,
        speaker: str,
        content: str,
        position: PositionVector,
        rci_score: float = 0.0,
        epistemic_tension: float = 0.0,
        local_concession: float = 0.0,
        evidence_weight: float = 0.0,
        is_intercepted: bool = False,
        is_self_corrected: bool = False,
        original_draft: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record a single conversational turn in persistent memory."""
        self.upsert_session(session_id)
        now = time.time()
        pos_json = json.dumps(position.values)
        meta_json = json.dumps(metadata or {})

        conn = get_db_connection(self.db_path)
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO turns (
                    session_id, turn_index, speaker, content, position_json,
                    rci_score, epistemic_tension, local_concession, evidence_weight,
                    is_intercepted, is_self_corrected, original_draft, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    turn_index,
                    speaker,
                    content,
                    pos_json,
                    rci_score,
                    epistemic_tension,
                    local_concession,
                    evidence_weight,
                    1 if is_intercepted else 0,
                    1 if is_self_corrected else 0,
                    original_draft,
                    meta_json,
                    now,
                ),
            )
            turn_id = cursor.lastrowid or 0
        conn.close()
        return turn_id

    def record_propositions(
        self,
        session_id: str,
        turn_index: int,
        claims: Sequence[Dict[str, Any]],
    ) -> None:
        """Upsert discrete extracted claims and propositions into the knowledge store."""
        now = time.time()
        conn = get_db_connection(self.db_path)
        with conn:
            for c in claims:
                claim_text = c.get("claim_text", "")
                if not claim_text:
                    continue
                claim_type = c.get("claim_type", "empirical")
                quantities = json.dumps(c.get("quantities", []))
                veracity = float(c.get("veracity", 1.0))
                constraint_pwr = float(c.get("constraint_power", 1.0))
                we = float(c.get("evidence_weight", 0.0))
                status = c.get("status", "VERIFIED" if we > 0.3 else "UNGROUNDED")
                falsification_proof = c.get("falsification_proof", None)

                # Check if claim text already recorded in this session or globally
                cursor = conn.execute(
                    "SELECT id, occurrence_count FROM propositions WHERE claim_text = ?",
                    (claim_text,),
                )
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE propositions SET
                            occurrence_count = occurrence_count + 1,
                            last_seen_at = ?,
                            veracity = ?,
                            constraint_power = ?,
                            evidence_weight = ?,
                            status = ?,
                            falsification_proof = COALESCE(?, falsification_proof)
                        WHERE id = ?
                        """,
                        (now, veracity, constraint_pwr, we, status, falsification_proof, row["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO propositions (
                            session_id, turn_index, claim_text, claim_type,
                            quantities_json, veracity, constraint_power, evidence_weight,
                            status, falsification_proof, occurrence_count, first_seen_at, last_seen_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """,
                        (
                            session_id,
                            turn_index,
                            claim_text,
                            claim_type,
                            quantities,
                            veracity,
                            constraint_pwr,
                            we,
                            status,
                            falsification_proof,
                            now,
                            now,
                        ),
                    )
        conn.close()

    def record_citations(
        self,
        session_id: str,
        turn_index: int,
        papers: Sequence[Dict[str, Any]],
    ) -> None:
        """Record verified scientific literature citations."""
        now = time.time()
        conn = get_db_connection(self.db_path)
        with conn:
            for p in papers:
                title = p.get("title", "")
                if not title:
                    continue
                doi = p.get("doi", "")
                authors = json.dumps(p.get("authors", []))
                year = p.get("year", None)
                venue = p.get("journal_or_venue", "")
                cit_count = int(p.get("citation_count", 0))
                abstract = p.get("abstract", "")

                conn.execute(
                    """
                    INSERT INTO citations (
                        doi, title, authors_json, year, venue, citation_count,
                        abstract, session_id, turn_index, first_cited_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doi,
                        title,
                        authors,
                        year,
                        venue,
                        cit_count,
                        abstract,
                        session_id,
                        turn_index,
                        now,
                    ),
                )
        conn.close()

    def find_cross_session_claims(
        self,
        claim_query: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search cross-session propositions matching a query string."""
        conn = get_db_connection(self.db_path)
        query = "SELECT * FROM propositions WHERE claim_text LIKE ?"
        params: List[Any] = [f"%{claim_query}%"]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY occurrence_count DESC, last_seen_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return results

    def list_propositions(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List propositions across all recorded sessions."""
        conn = get_db_connection(self.db_path)
        if status:
            rows = conn.execute(
                "SELECT * FROM propositions WHERE status = ? ORDER BY last_seen_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM propositions ORDER BY last_seen_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return results

    def get_session_turns(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all recorded turns for a specific session ordered by turn index."""
        conn = get_db_connection(self.db_path)
        rows = conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC",
            (session_id,),
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return results

    def get_session_citations(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all citations associated with a specific session."""
        conn = get_db_connection(self.db_path)
        rows = conn.execute(
            "SELECT * FROM citations WHERE session_id = ? ORDER BY turn_index ASC",
            (session_id,),
        ).fetchall()
        results = [dict(r) for r in rows]
        conn.close()
        return results


    def get_epistemic_knowledge_graph(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct an interactive node-link graph of Sessions, Turns, Claims, and Citations."""
        conn = get_db_connection(self.db_path)

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        # 1. Fetch Sessions
        if session_id:
            sessions = conn.execute(
                "SELECT session_id, model_name FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        else:
            sessions = conn.execute(
                "SELECT session_id, model_name FROM sessions ORDER BY updated_at DESC LIMIT 10"
            ).fetchall()

        sess_ids = [s["session_id"] for s in sessions]

        for s in sessions:
            nodes.append(
                {
                    "id": f"session:{s['session_id']}",
                    "label": f"Session: {s['session_id'][:10]}...",
                    "type": "session",
                    "model": s["model_name"],
                }
            )

        if not sess_ids:
            conn.close()
            return {"nodes": nodes, "links": links}

        placeholders = ",".join("?" for _ in sess_ids)

        # 2. Fetch Turns
        turns = conn.execute(
            f"SELECT id, session_id, turn_index, speaker, rci_score, evidence_weight, is_intercepted, is_self_corrected FROM turns WHERE session_id IN ({placeholders}) ORDER BY turn_index ASC",
            sess_ids,
        ).fetchall()

        for t in turns:
            turn_node_id = f"turn:{t['session_id']}:{t['turn_index']}"
            status_label = "CLEARED"
            if t["is_intercepted"]:
                status_label = "INTERCEPTED"
            elif t["is_self_corrected"]:
                status_label = "SELF_CORRECTED"

            nodes.append(
                {
                    "id": turn_node_id,
                    "label": f"Turn {t['turn_index']} ({t['speaker']})",
                    "type": "turn",
                    "speaker": t["speaker"],
                    "rci": t["rci_score"],
                    "evidence_we": t["evidence_weight"],
                    "status": status_label,
                }
            )
            # Link session -> turn
            links.append(
                {
                    "source": f"session:{t['session_id']}",
                    "target": turn_node_id,
                    "relation": "has_turn",
                }
            )

        # 3. Fetch Propositions
        props = conn.execute(
            f"SELECT id, session_id, turn_index, claim_text, claim_type, status, evidence_weight FROM propositions WHERE session_id IN ({placeholders})",
            sess_ids,
        ).fetchall()

        for p in props:
            prop_node_id = f"claim:{p['id']}"
            short_claim = p["claim_text"][:40] + ("..." if len(p["claim_text"]) > 40 else "")
            nodes.append(
                {
                    "id": prop_node_id,
                    "label": short_claim,
                    "full_text": p["claim_text"],
                    "type": "claim",
                    "claim_type": p["claim_type"],
                    "status": p["status"],
                    "evidence_weight": p["evidence_weight"],
                }
            )
            # Link turn -> claim
            turn_node_id = f"turn:{p['session_id']}:{p['turn_index']}"
            links.append(
                {
                    "source": turn_node_id,
                    "target": prop_node_id,
                    "relation": "asserts_claim",
                }
            )

        # 4. Fetch Citations
        cits = conn.execute(
            f"SELECT id, doi, title, citation_count, venue, session_id, turn_index FROM citations WHERE session_id IN ({placeholders})",
            sess_ids,
        ).fetchall()

        for c in cits:
            cit_node_id = f"paper:{c['id']}"
            short_title = c["title"][:40] + ("..." if len(c["title"]) > 40 else "")
            nodes.append(
                {
                    "id": cit_node_id,
                    "label": short_title,
                    "full_title": c["title"],
                    "doi": c["doi"],
                    "type": "paper",
                    "citation_count": c["citation_count"],
                    "venue": c["venue"],
                }
            )
            # Link turn -> paper
            turn_node_id = f"turn:{c['session_id']}:{c['turn_index']}"
            links.append(
                {
                    "source": turn_node_id,
                    "target": cit_node_id,
                    "relation": "cites_literature",
                }
            )

        conn.close()
        return {"nodes": nodes, "links": links}
