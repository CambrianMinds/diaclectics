"""SQLite Database Initialization & Connection Management for Epistemic Memory."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.getenv("DIACLECTICS_DB_PATH", ".cache/diaclectics.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a thread-safe connection to the SQLite database with WAL mode."""
    target_path = Path(db_path or DEFAULT_DB_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database tables for sessions, turns, propositions, and citations."""
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                model_name TEXT,
                axis_config_json TEXT
            );

            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                content TEXT NOT NULL,
                position_json TEXT NOT NULL,
                rci_score REAL DEFAULT 0.0,
                epistemic_tension REAL DEFAULT 0.0,
                local_concession REAL DEFAULT 0.0,
                evidence_weight REAL DEFAULT 0.0,
                is_intercepted INTEGER DEFAULT 0,
                is_self_corrected INTEGER DEFAULT 0,
                original_draft TEXT,
                metadata_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS propositions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                claim_type TEXT NOT NULL,
                quantities_json TEXT,
                veracity REAL DEFAULT 1.0,
                constraint_power REAL DEFAULT 1.0,
                evidence_weight REAL DEFAULT 0.0,
                status TEXT DEFAULT 'UNGROUNDED',
                falsification_proof TEXT,
                occurrence_count INTEGER DEFAULT 1,
                first_seen_at REAL NOT NULL,
                last_seen_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT,
                title TEXT NOT NULL,
                authors_json TEXT,
                year INTEGER,
                venue TEXT,
                citation_count INTEGER DEFAULT 0,
                abstract TEXT,
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                first_cited_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, turn_index);
            CREATE INDEX IF NOT EXISTS idx_propositions_status ON propositions(status);
            CREATE INDEX IF NOT EXISTS idx_propositions_claim ON propositions(claim_text);
            CREATE INDEX IF NOT EXISTS idx_citations_doi ON citations(doi);
            """
        )
    conn.close()
