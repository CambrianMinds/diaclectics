"""Zero-API-Cost Local Hybrid Search Literature & Axiom Index.

Combines SQLite FTS5 (BM25 keyword search) and local dense vector embeddings
to provide fast, zero-cost, offline academic and domain-knowledge retrieval.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field

from src.storage.db import get_db_connection, init_db
from src.verifier.search_verifier import AcademicPaper

logger = logging.getLogger("diaclectics.local_index")

EMBEDDING_DIM = 384


class LocalVectorizer:
    """Fast, local, zero-API-cost sub-word hashing and semantic projection vectorizer."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim
        self._has_fastembed = False
        self._fastembed_model = None
        self._init_fastembed()

    def _init_fastembed(self) -> None:
        """Attempt to initialize fastembed if installed in the environment."""
        try:
            from fastembed import TextEmbedding  # type: ignore

            self._fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self._has_fastembed = True
            logger.info("LocalVectorizer initialized with FastEmbed ONNX backend.")
        except Exception:
            self._has_fastembed = False

    def embed_text(self, text: str) -> List[float]:
        """Generate a normalized dense vector embedding for input text."""
        if not text or not text.strip():
            return [0.0] * self.dim

        if self._has_fastembed and self._fastembed_model:
            try:
                embeddings = list(self._fastembed_model.embed([text]))
                vec = embeddings[0]
                norm = np.linalg.norm(vec)
                if norm > 1e-9:
                    vec = vec / norm
                return vec.tolist()
            except Exception as e:
                logger.debug("FastEmbed error (%s), falling back to local projection", e)

        # High-speed deterministic subword n-gram hashing projection (384 dimensions)
        vec = np.zeros(self.dim, dtype=np.float32)
        clean = re.sub(r"[^\w\s]", " ", text.lower()).strip()
        words = clean.split()

        for w in words:
            # Word level feature
            h_word = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[h_word] += 1.5

            # 3-gram and 4-gram character subwords
            if len(w) >= 3:
                for n in range(3, min(6, len(w) + 1)):
                    for i in range(len(w) - n + 1):
                        ngram = w[i : i + n]
                        h_sub = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16) % self.dim
                        vec[h_sub] += 0.8

        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec.tolist()


class LocalKnowledgeIndex:
    """SQLite FTS5 + Dense Vector Hybrid Knowledge Index."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        vectorizer: Optional[LocalVectorizer] = None,
    ) -> None:
        self.db_path = db_path
        init_db(self.db_path)
        self.vectorizer = vectorizer or LocalVectorizer()

    def index_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        doi: Optional[str] = None,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None,
        venue: Optional[str] = None,
        citation_count: int = 0,
    ) -> None:
        """Index a document into both SQLite FTS5 table and vector store."""
        combined_text = f"{title}\n{content}"
        vec = self.vectorizer.embed_text(combined_text)
        vec_json = json.dumps(vec)
        authors_json = json.dumps(authors or [])
        now = time.time()

        conn = get_db_connection(self.db_path)
        with conn:
            # 1. Insert/Update local_corpus
            conn.execute(
                """
                INSERT INTO local_corpus (
                    doc_id, title, content, doi, authors_json, year, venue, citation_count, vector_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    doi = excluded.doi,
                    authors_json = excluded.authors_json,
                    year = excluded.year,
                    venue = excluded.venue,
                    citation_count = excluded.citation_count,
                    vector_json = excluded.vector_json;
                """,
                (doc_id, title, content, doi, authors_json, year, venue, citation_count, vec_json, now),
            )

            # 2. Insert into FTS5
            # Delete old FTS row if exists
            conn.execute("DELETE FROM local_corpus_fts WHERE doc_id = ?", (doc_id,))
            conn.execute(
                "INSERT INTO local_corpus_fts (doc_id, title, content) VALUES (?, ?, ?)",
                (doc_id, title, content),
            )
        conn.close()
        logger.debug("Indexed document %s into LocalKnowledgeIndex", doc_id)

    def index_paper(self, paper: AcademicPaper) -> None:
        """Convenience method to index an AcademicPaper object."""
        doc_id = paper.doi or f"paper_{hashlib.md5(paper.title.encode('utf-8')).hexdigest()[:12]}"
        content = paper.abstract or paper.title
        self.index_document(
            doc_id=doc_id,
            title=paper.title,
            content=content,
            doi=paper.doi,
            authors=paper.authors,
            year=paper.publication_year,
            venue=paper.journal_or_venue,
            citation_count=paper.citation_count,
        )

    def index_directory(self, dir_path: Union[str, Path], glob_pattern: str = "*.md") -> int:
        """Scan a directory and index all matching markdown / text files."""
        folder = Path(dir_path)
        if not folder.exists():
            return 0

        indexed_count = 0
        for p in folder.glob(glob_pattern):
            try:
                text = p.read_text(encoding="utf-8")
                doc_id = f"file_{p.stem}"
                title = p.stem.replace("_", " ").replace("-", " ").title()
                self.index_document(
                    doc_id=doc_id,
                    title=title,
                    content=text,
                    venue=str(p.name),
                )
                indexed_count += 1
            except Exception as e:
                logger.warning("Failed to index file %s: %s", p, e)

        return indexed_count

    def search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> List[AcademicPaper]:
        """Perform hybrid BM25 + Dense Vector search over the local corpus."""
        if not query or not query.strip():
            return []

        conn = get_db_connection(self.db_path)

        # 1. Keyword search via FTS5
        # Clean query tokens for FTS5 syntax
        clean_tokens = [re.sub(r"[^\w]", "", tok) for tok in query.split() if len(tok) > 1]
        fts_scores: Dict[str, float] = {}

        if clean_tokens:
            fts_query = " OR ".join(f'"{tok}"*' for tok in clean_tokens[:8])
            try:
                rows = conn.execute(
                    """
                    SELECT doc_id, rank
                    FROM local_corpus_fts
                    WHERE local_corpus_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT 50;
                    """,
                    (fts_query,),
                ).fetchall()
                # In SQLite FTS5, lower rank is better (more negative). Normalize to [0, 1].
                if rows:
                    raw_ranks = [abs(r["rank"]) for r in rows]
                    max_rank = max(raw_ranks) if raw_ranks else 1.0
                    min_rank = min(raw_ranks) if raw_ranks else 0.0
                    span = max(max_rank - min_rank, 1e-6)
                    for r in rows:
                        norm_kw = 1.0 - (abs(r["rank"]) - min_rank) / span
                        fts_scores[r["doc_id"]] = max(0.1, norm_kw)
            except Exception as e:
                logger.debug("FTS5 query failed: %s", e)

        # 2. Vector search
        q_vec = np.array(self.vectorizer.embed_text(query), dtype=np.float32)

        # Fetch all candidate documents (or all if corpus is small)
        all_docs = conn.execute("SELECT * FROM local_corpus").fetchall()
        conn.close()

        if not all_docs:
            return []

        scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

        for row in all_docs:
            doc_id = row["doc_id"]
            vec_data = row["vector_json"]
            v_score = 0.0
            if vec_data:
                try:
                    d_vec = np.array(json.loads(vec_data), dtype=np.float32)
                    v_score = float(np.dot(q_vec, d_vec))
                except Exception:
                    pass

            kw_score = fts_scores.get(doc_id, 0.0)
            hybrid_score = (vector_weight * max(0.0, v_score)) + (keyword_weight * kw_score)

            if hybrid_score > 0.05 or kw_score > 0.0:
                scored_candidates.append((hybrid_score, dict(row)))

        # Sort by hybrid score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results: List[AcademicPaper] = []
        for score, row in scored_candidates[:top_k]:
            authors = json.loads(row.get("authors_json") or "[]")
            paper = AcademicPaper(
                title=row["title"],
                doi=row.get("doi"),
                authors=authors,
                publication_year=row.get("year"),
                journal_or_venue=row.get("venue"),
                abstract=row["content"][:600],
                citation_count=row.get("citation_count", 0),
                source_api="LocalHybridIndex",
            )
            results.append(paper)

        return results
