"""Real-Time Search & Knowledge Grounding Verifier.

Queries external literature, academic repositories, and knowledge databases to verify
falsifiable propositions and gather real-time ground truth context.
"""

from __future__ import annotations

import hashlib
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


class SearchResult(BaseModel):
    """Result of a real-time web/literature verification query."""

    query: str
    snippets: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    is_grounded: bool = False
    cached: bool = False


class SearchVerifier:
    """Real-time search verification client with disk caching."""

    def __init__(
        self,
        cache_file: Optional[str] = ".cache/search_cache.json",
        timeout: float = 6.0,
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
        """Search the web or literature for ground truth context on a proposition."""
        query = query.strip()
        if not query:
            return SearchResult(query=query, snippets=[], sources=[], is_grounded=False)

        q_hash = self._hash(query)
        with self._lock:
            if q_hash in self._cache:
                data = self._cache[q_hash]
                return SearchResult(
                    query=query,
                    snippets=data.get("snippets", []),
                    sources=data.get("sources", []),
                    is_grounded=bool(data.get("snippets")),
                    cached=True,
                )

        # Execute live search via DuckDuckGo HTML / Instant API or Fallback
        snippets: List[str] = []
        sources: List[str] = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                # Extract text snippets from DuckDuckGo HTML results
                raw_snippets = re.findall(
                    r'<a class="result__snippet[^>]*>(.*?)</a>',
                    resp.text,
                    re.DOTALL,
                )
                raw_urls = re.findall(
                    r'<a class="result__url[^>]*href="([^"]+)"',
                    resp.text,
                )
                for s in raw_snippets[:max_results]:
                    # Clean HTML tags
                    clean_s = re.sub(r"<[^>]+>", "", s).strip()
                    if clean_s:
                        snippets.append(clean_s)
                for u in raw_urls[:max_results]:
                    sources.append(u.strip())
        except Exception as e:
            logger.debug(f"Search request failed for '{query}': {e}")

        is_grounded = len(snippets) > 0

        # Cache result
        with self._lock:
            self._cache[q_hash] = {
                "snippets": snippets,
                "sources": sources,
                "timestamp": time.time(),
            }
            self._save_cache()

        return SearchResult(
            query=query,
            snippets=snippets,
            sources=sources,
            is_grounded=is_grounded,
            cached=False,
        )
