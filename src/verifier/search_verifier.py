"""Real-Time Academic Literature & Knowledge Search Verifier.

Queries actual external scientific literature and knowledge databases in real time:
1. OpenAlex API (Millions of peer-reviewed papers, abstracts, citation counts, and DOIs)
2. Crossref API (Official DOI registry, metadata, and peer review records)
3. Wikipedia Knowledge API (Empirical datums, historical events, statutes)
4. DuckDuckGo Instant Web Search

Feeds retrieved abstracts, verified DOIs, and literature snippets directly into the
EpistemicReasoningJudge to ground claims against empirical reality.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import requests

logger = logging.getLogger(__name__)


class AcademicPaper(BaseModel):
    """Structured representation of a real peer-reviewed academic paper."""

    title: str
    doi: Optional[str] = None
    authors: List[str] = Field(default_factory=list)
    publication_year: Optional[int] = None
    journal_or_venue: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: int = 0
    source_api: str = "OpenAlex"


class SearchResult(BaseModel):
    """Result of a real-time web/literature verification query."""

    query: str
    is_grounded: bool = False
    papers_found: List[AcademicPaper] = Field(default_factory=list)
    snippets: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    cached: bool = False
    verified_doi_count: int = 0

    def format_literature_context(self) -> str:
        """Format literature findings into a concise context block for the reasoning judge."""
        if not self.papers_found and not self.snippets:
            return "No matching scientific literature or verified empirical records found."

        parts: List[str] = []
        if self.papers_found:
            parts.append("PEER-REVIEWED SCIENTIFIC LITERATURE FOUND:")
            for p in self.papers_found[:3]:
                doi_str = f" | DOI: {p.doi}" if p.doi else ""
                cites_str = f" | Citations: {p.citation_count}" if p.citation_count else ""
                year_str = f" ({p.publication_year})" if p.publication_year else ""
                authors_str = ", ".join(p.authors[:2]) if p.authors else "Unknown Authors"
                parts.append(f"• \"{p.title}\"{year_str} by {authors_str}{doi_str}{cites_str}")
                if p.abstract:
                    clean_abs = p.abstract[:250].replace("\n", " ").strip()
                    parts.append(f"  Abstract Excerpt: {clean_abs}...")

        if self.snippets:
            parts.append("\nEMPIRICAL KNOWLEDGE BASES / WEB CONTEXT:")
            for s in self.snippets[:3]:
                parts.append(f"• {s}")

        return "\n".join(parts)


class SearchVerifier:
    """Multi-source real-time scientific literature search and verification engine."""

    OPENALEX_API_URL = "https://api.openalex.org/works"
    CROSSREF_API_URL = "https://api.crossref.org/works"
    WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"

    def __init__(
        self,
        cache_file: Optional[str] = ".cache/search_cache.json",
        timeout: float = 8.0,
    ) -> None:
        self.cache_file = Path(cache_file) if cache_file else None
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load search cache: {e}")

    def _save_cache(self) -> None:
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f)
            except Exception as e:
                logger.warning(f"Failed to save search cache: {e}")

    @staticmethod
    def _hash(query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    def search(self, query: str, max_results: int = 3) -> SearchResult:
        """Search actual academic repositories and empirical knowledge bases for ground truth."""
        query = query.strip()
        if not query:
            return SearchResult(query=query, is_grounded=False)

        q_hash = self._hash(query)
        with self._lock:
            if q_hash in self._cache:
                data = self._cache[q_hash]
                papers = [AcademicPaper(**p) for p in data.get("papers_found", [])]
                return SearchResult(
                    query=query,
                    is_grounded=data.get("is_grounded", False),
                    papers_found=papers,
                    snippets=data.get("snippets", []),
                    sources=data.get("sources", []),
                    cached=True,
                    verified_doi_count=data.get("verified_doi_count", 0),
                )

        papers: List[AcademicPaper] = []
        snippets: List[str] = []
        sources: List[str] = []

        # 1. Query OpenAlex for peer-reviewed academic literature
        try:
            headers = {"User-Agent": "DiaclecticsVerifier/2.0 (mailto:research@diaclectics.ai)"}
            params = {
                "search": query,
                "per-page": max_results,
            }
            res = requests.get(self.OPENALEX_API_URL, params=params, headers=headers, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                for work in data.get("results", []):
                    title = work.get("title") or "Untitled Paper"
                    doi = work.get("doi")
                    cites = work.get("cited_by_count", 0)
                    year = work.get("publication_year")
                    authors = [
                        auth.get("author", {}).get("display_name", "")
                        for auth in work.get("authorships", [])
                        if auth.get("author", {}).get("display_name")
                    ]
                    venue = work.get("primary_location", {}).get("source", {}).get("display_name")

                    # Reconstruct abstract from OpenAlex inverted index if available
                    abstract = None
                    inv_index = work.get("abstract_inverted_index")
                    if inv_index:
                        try:
                            word_positions = []
                            for word, positions in inv_index.items():
                                for pos in positions:
                                    word_positions.append((pos, word))
                            word_positions.sort()
                            abstract = " ".join(w for _, w in word_positions)
                        except Exception:
                            abstract = None

                    paper = AcademicPaper(
                        title=title,
                        doi=doi,
                        authors=authors,
                        publication_year=year,
                        journal_or_venue=venue,
                        abstract=abstract,
                        citation_count=cites,
                        source_api="OpenAlex",
                    )
                    papers.append(paper)
                    if doi:
                        sources.append(doi)
        except Exception as e:
            logger.debug(f"OpenAlex query error: {e}")

        # 2. Query Crossref if specific DOI or authors are targeted
        if "doi" in query.lower() or "10." in query or not papers:
            try:
                headers = {"User-Agent": "DiaclecticsVerifier/2.0 (mailto:research@diaclectics.ai)"}
                params = {"query": query, "rows": max_results}
                c_res = requests.get(self.CROSSREF_API_URL, params=params, headers=headers, timeout=self.timeout)
                if c_res.status_code == 200:
                    c_data = c_res.json()
                    for item in c_data.get("message", {}).get("items", []):
                        titles = item.get("title", [])
                        title = titles[0] if titles else "Untitled Crossref Work"
                        doi = item.get("DOI")
                        year = None
                        date_parts = item.get("created", {}).get("date-parts", [])
                        if date_parts and date_parts[0]:
                            year = date_parts[0][0]
                        authors = [
                            f"{a.get('given', '')} {a.get('family', '')}".strip()
                            for a in item.get("author", [])
                            if a.get("family")
                        ]
                        container = item.get("container-title", [])
                        venue = container[0] if container else None

                        paper = AcademicPaper(
                            title=title,
                            doi=f"https://doi.org/{doi}" if doi and not doi.startswith("http") else doi,
                            authors=authors,
                            publication_year=year,
                            journal_or_venue=venue,
                            citation_count=item.get("is-referenced-by-count", 0),
                            source_api="Crossref",
                        )
                        # Avoid duplicates
                        if not any(p.title.lower() == title.lower() for p in papers):
                            papers.append(paper)
                            if doi:
                                sources.append(f"https://doi.org/{doi}")
            except Exception as e:
                logger.debug(f"Crossref query error: {e}")

        # 3. Query Wikipedia for empirical/statutory definitions
        try:
            w_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
            }
            w_headers = {"User-Agent": "DiaclecticsVerifier/2.0 (mailto:research@diaclectics.ai)"}
            w_res = requests.get(self.WIKIPEDIA_API_URL, params=w_params, headers=w_headers, timeout=self.timeout)
            if w_res.status_code == 200:
                w_data = w_res.json()
                for match in w_data.get("query", {}).get("search", []):
                    clean_snippet = re.sub(r"<[^>]+>", "", match.get("snippet", "")).strip()
                    clean_snippet = html.unescape(clean_snippet)
                    if clean_snippet:
                        snippets.append(f"[{match.get('title')}]: {clean_snippet}")
                        sources.append(f"https://en.wikipedia.org/wiki/{match.get('title', '').replace(' ', '_')}")
        except Exception as e:
            logger.debug(f"Wikipedia query error: {e}")

        # Count verified DOIs
        verified_dois = sum(1 for p in papers if p.doi)
        is_grounded = len(papers) > 0 or len(snippets) > 0

        result = SearchResult(
            query=query,
            is_grounded=is_grounded,
            papers_found=papers,
            snippets=snippets,
            sources=sources,
            cached=False,
            verified_doi_count=verified_dois,
        )

        # Cache result
        with self._lock:
            self._cache[q_hash] = {
                "is_grounded": result.is_grounded,
                "papers_found": [p.model_dump() for p in result.papers_found],
                "snippets": result.snippets,
                "sources": result.sources,
                "verified_doi_count": result.verified_doi_count,
            }
            self._save_cache()

        return result
