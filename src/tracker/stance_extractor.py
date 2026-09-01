"""Automated Epistemic Stance Extractor.

Extracts stance vectors and polarity scalars from dialogue text using:
1. Semantic projection via OpenRouter embeddings (liquid/lfm-2.5-embedding-350m:free) with strict rate-limiting, caching, and exponential backoff.
2. Fast lexical/structural fallback parser.
3. Composite fallback cascade.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
from pydantic import BaseModel, Field
import requests

from src.tracker.state_vector import PositionVector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiting, Caching & OpenRouter Embedding Client
# ---------------------------------------------------------------------------


class EmbeddingRateLimiter:
    """Thread-safe rate limiter with minimum request intervals and token bucket."""

    def __init__(
        self,
        max_requests_per_minute: int = 15,
        min_interval_seconds: float = 2.0,
        max_retries: int = 5,
        base_backoff_seconds: float = 3.0,
    ) -> None:
        self.max_rpm = max_requests_per_minute
        self.min_interval = min_interval_seconds
        self.max_retries = max_retries
        self.base_backoff = base_backoff_seconds
        self._lock = threading.Lock()
        self._last_request_time: float = 0.0
        self._request_timestamps: List[float] = []

    def acquire(self) -> None:
        """Enforce rate limit spacing before making an outgoing request."""
        with self._lock:
            now = time.time()

            # Clean timestamps older than 60 seconds
            self._request_timestamps = [
                t for t in self._request_timestamps if now - t < 60.0
            ]

            # If requests in last minute >= max_rpm, wait for earliest to expire
            if len(self._request_timestamps) >= self.max_rpm:
                sleep_needed = 60.0 - (now - self._request_timestamps[0]) + 0.1
                if sleep_needed > 0:
                    time.sleep(sleep_needed)
                    now = time.time()
                    self._request_timestamps = [
                        t for t in self._request_timestamps if now - t < 60.0
                    ]

            # Enforce minimum interval between consecutive calls
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
                now = time.time()

            self._last_request_time = now
            self._request_timestamps.append(now)


class EmbeddingCache:
    """Cache keyed by SHA-256 text hash with optional disk persistence."""

    def __init__(self, cache_file: Optional[str] = ".cache/embeddings.json") -> None:
        self.cache_file = Path(cache_file) if cache_file else None
        self._cache: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    @staticmethod
    def _hash(text: str, model: str) -> str:
        return hashlib.sha256(f"{model}::{text.strip()}".encode("utf-8")).hexdigest()

    def _load_from_disk(self) -> None:
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load disk embedding cache: {e}")

    def _save_to_disk(self) -> None:
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f)
            except Exception as e:
                logger.warning(f"Failed to save disk embedding cache: {e}")

    def get(self, text: str, model: str) -> Optional[List[float]]:
        with self._lock:
            return self._cache.get(self._hash(text, model))

    def set(self, text: str, model: str, embedding: List[float]) -> None:
        with self._lock:
            self._cache[self._hash(text, model)] = embedding
            # Periodically or immediately persist
            if len(self._cache) % 5 == 0:
                self._save_to_disk()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class OpenRouterEmbeddingClient:
    """Client for generating text embeddings via OpenRouter with rate limiting and caching."""

    DEFAULT_MODEL = "liquid/lfm-2.5-embedding-350m:free"
    API_URL = "https://openrouter.ai/api/v1/embeddings"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        rate_limiter: Optional[EmbeddingRateLimiter] = None,
        cache: Optional[EmbeddingCache] = None,
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        )
        self.model = model
        self.rate_limiter = rate_limiter or EmbeddingRateLimiter()
        self.cache = cache or EmbeddingCache()

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 500) -> List[str]:
        """Split text into chunks strictly within the 512 token limit (~500 chars / ~120-150 tokens)."""
        text = text.strip()
        if len(text) <= max_chars:
            return [text]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= max_chars:
                current = (current + "\n\n" + p).strip()
            else:
                if current:
                    chunks.append(current)
                if len(p) <= max_chars:
                    current = p
                else:
                    for i in range(0, len(p), max_chars):
                        sub = p[i : i + max_chars].strip()
                        if sub:
                            chunks.append(sub)
                    current = ""
        if current:
            chunks.append(current)
        # Select representative chunks across the essay to stay within rate limits
        if len(chunks) > 3:
            chunks = [chunks[0], chunks[len(chunks) // 2], chunks[-1]]
        return [c for c in chunks if c.strip()] or [text[:max_chars]]

    def get_embedding(self, text: str) -> List[float]:
        """Fetch embedding for a string, chunking long essays and averaging vectors."""
        if not text or not text.strip():
            return [0.0] * 1024

        cached = self.cache.get(text, self.model)
        if cached is not None:
            return cached

        chunks = self._chunk_text(text)
        if len(chunks) == 1:
            embeddings = self._fetch_raw_batch([chunks[0]])
            res = embeddings[0] if embeddings else [0.0] * 1024
        else:
            chunk_embeddings = self._fetch_raw_batch(chunks)
            if not chunk_embeddings:
                return [0.0] * 1024
            # Vector average
            dim = len(chunk_embeddings[0])
            avg_vec = [
                sum(chunk_embeddings[k][i] for k in range(len(chunk_embeddings)))
                / len(chunk_embeddings)
                for i in range(dim)
            ]
            # L2 normalize
            mag = math.sqrt(sum(x * x for x in avg_vec))
            res = [x / mag for x in avg_vec] if mag > 0 else avg_vec

        self.cache.set(text, self.model, res)
        return res

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Fetch embeddings for a list of strings."""
        return [self.get_embedding(t) for t in texts]

    def _fetch_raw_batch(self, texts: List[str]) -> List[List[float]]:
        """Internal worker fetching raw embeddings with caching and rate limiting."""
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        for i, text in enumerate(texts):
            cached = self.cache.get(text, self.model)
            if cached is not None:
                results[i] = cached
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if not missing_texts:
            return [r for r in results if r is not None]

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. Provide an API key or set OPENROUTER_API_KEY in the environment."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/justin-bogner/diaclectics",
            "X-Title": "Relational Contracting Engine",
        }

        # Process in chunks of up to 16 to respect request payload sizes
        chunk_size = 16
        for c_start in range(0, len(missing_texts), chunk_size):
            chunk_texts = missing_texts[c_start : c_start + chunk_size]
            chunk_indices = missing_indices[c_start : c_start + chunk_size]

            attempt = 0
            while attempt < self.rate_limiter.max_retries:
                self.rate_limiter.acquire()
                try:
                    payload = {"model": self.model, "input": chunk_texts}
                    response = requests.post(
                        self.API_URL, headers=headers, json=payload, timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        embed_list = data.get("data", [])
                        for idx_in_chunk, item in enumerate(embed_list):
                            emb = item.get("embedding", [])
                            global_idx = chunk_indices[idx_in_chunk]
                            results[global_idx] = emb
                            self.cache.set(chunk_texts[idx_in_chunk], self.model, emb)
                        break

                    elif response.status_code == 429:
                        # Rate limited: check Retry-After header or exponential backoff
                        retry_after = response.headers.get("Retry-After")
                        wait_time = (
                            float(retry_after)
                            if retry_after and retry_after.isdigit()
                            else self.rate_limiter.base_backoff * (2**attempt)
                        )
                        logger.warning(
                            f"OpenRouter 429 Rate Limit hit. Backing off for {wait_time:.1f}s (attempt {attempt+1})"
                        )
                        time.sleep(wait_time)
                        attempt += 1

                    else:
                        raise RuntimeError(
                            f"OpenRouter API error {response.status_code}: {response.text}"
                        )

                except requests.RequestException as e:
                    attempt += 1
                    if attempt >= self.rate_limiter.max_retries:
                        raise RuntimeError(
                            f"OpenRouter network request failed after {self.rate_limiter.max_retries} attempts: {e}"
                        )
                    time.sleep(self.rate_limiter.base_backoff * (2**attempt))

        return [r if r is not None else [0.0] * 1024 for r in results]


# ---------------------------------------------------------------------------
# Stance Extractor Data Models & Base Interface
# ---------------------------------------------------------------------------


class PolarAxis(BaseModel):
    """Single polar axis definition representing a specific epistemic dimension."""

    name: str = Field(description="Unique identifier/slug for the epistemic dimension.")
    thesis_statement: str = Field(
        description="Positive anchor (+1.0), representing the affirmative/alternative hypothesis."
    )
    antithesis_statement: str = Field(
        description="Negative anchor (-1.0), representing the baseline/null/orthodox hypothesis."
    )
    description: Optional[str] = None


class PolarAnchor(BaseModel):
    """Pair of opposing thesis/antithesis statements defining a single epistemic axis."""

    thesis_statement: str = Field(
        description="Positive anchor (+1.0), representing the affirmative/alternative hypothesis."
    )
    antithesis_statement: str = Field(
        description="Negative anchor (-1.0), representing the baseline/null/orthodox hypothesis."
    )
    axis_name: str = "general_stance"


class MultiAxisPolarAnchor(BaseModel):
    """Multi-dimensional epistemic anchor defining N concurrent polar axes."""

    axes: List[PolarAxis] = Field(default_factory=list)

    @classmethod
    def default_tri_axial_anchor(cls) -> MultiAxisPolarAnchor:
        """Standard 3D epistemic anchor for deep-time physical & archaeological forensics."""
        return cls(
            axes=[
                PolarAxis(
                    name="kinematics_and_toolmarks",
                    thesis_statement="Precision stonework exhibits mechanical rotary tool kinematics, feed spirals, and advanced machining.",
                    antithesis_statement="Orthodox Bronze Age copper tools, manual sawing, and sand abrasive explain all stonework.",
                    description="Tool kinematics & feed rates vs. manual copper saws",
                ),
                PolarAxis(
                    name="stratigraphy_and_chronology",
                    thesis_statement="Megalithic structures, nanodiamonds, and microspherules predate the Younger Dryas impact boundary.",
                    antithesis_statement="All monumental construction dates strictly to the Dynastic Bronze/Iron Age orthodox timeline.",
                    description="Deep-time Pleistocene antiquity vs. Dynastic orthodox chronology",
                ),
                PolarAxis(
                    name="materials_and_mechanisms",
                    thesis_statement="Acoustic resonance, piezoelectric friction modulation, and phononic bandgaps enabled stone manipulation.",
                    antithesis_statement="Only conventional gravity ramps, wooden sledges, and sand jacks were physically used.",
                    description="Acoustic/physical mechanisms vs. conventional manual leverage",
                ),
            ]
        )

    def to_single_anchor(self, axis_idx: int = 0) -> PolarAnchor:
        """Convert a specific axis of the multi-anchor to a single PolarAnchor."""
        if not self.axes:
            return PolarAnchor(
                thesis_statement="Alternative hypothesis.",
                antithesis_statement="Orthodox hypothesis.",
            )
        target = self.axes[min(axis_idx, len(self.axes) - 1)]
        return PolarAnchor(
            thesis_statement=target.thesis_statement,
            antithesis_statement=target.antithesis_statement,
            axis_name=target.name,
        )


class StanceExtractionResult(BaseModel):
    """Result of automated stance extraction from raw text."""

    position: PositionVector
    scalar_stance: float = Field(
        description="Normalized primary stance scalar in [-1.0, 1.0]."
    )
    axis_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Stance coordinates broken down per individual polar axis.",
    )
    confidence: float = Field(
        default=1.0, description="Confidence metric for the extraction in [0.0, 1.0]."
    )
    primary_claims: List[str] = Field(default_factory=list)
    backend_used: str = "lexical"
    raw_text: str = ""


class BaseStanceExtractor(ABC):
    """Abstract interface for extracting stance vectors from text."""

    @abstractmethod
    def extract(
        self,
        text: str,
        anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> StanceExtractionResult:
        """Extract stance from raw text."""
        pass


# ---------------------------------------------------------------------------
# 1. Lexical / Rule-Based Stance Extractor (Fast Zero-Dependency Fallback)
# ---------------------------------------------------------------------------


class LexicalStanceExtractor(BaseStanceExtractor):
    """Rule-based stance extractor using negation, modality, affirmation, and contrast patterns."""

    def __init__(self) -> None:
        self._affirm_pattern = re.compile(
            r"\b(agree|support|confirm|validated|proven|demonstrates|superior|optimal|favor|accept|correct|true|accurate|right|genius|concede|abandon|surrender|brilliant|undeniably|unquestionably)\b",
            re.IGNORECASE,
        )
        self._negate_pattern = re.compile(
            r"\b(disagree|refute|falsified|incorrect|false|inaccurate|reject|inferior|flawed|unsupported|doubt|contrary)\b",
            re.IGNORECASE,
        )
        self._hedge_pattern = re.compile(
            r"\b(maybe|perhaps|possibly|plausible|uncertain|mixed|partially|inconclusive)\b",
            re.IGNORECASE,
        )

    def extract(
        self,
        text: str,
        anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> StanceExtractionResult:
        if not text or not text.strip():
            return StanceExtractionResult(
                position=PositionVector.from_scalar(0.0),
                scalar_stance=0.0,
                axis_scores={},
                confidence=0.0,
                primary_claims=[],
                backend_used="lexical",
                raw_text=text,
            )

        affirms = len(self._affirm_pattern.findall(text))
        negates = len(self._negate_pattern.findall(text))
        hedges = len(self._hedge_pattern.findall(text))

        raw_diff = affirms - negates
        total = affirms + negates + hedges

        if total == 0:
            scalar = 0.0
            confidence = 0.3
        else:
            scalar = raw_diff / max(1, (affirms + negates))
            # Dampen if heavy hedging
            if hedges > 0:
                scalar *= 1.0 / (1.0 + 0.5 * hedges)
            confidence = min(1.0, 0.4 + 0.15 * total)

        scalar = max(-1.0, min(1.0, round(scalar, 4)))

        axis_scores: Dict[str, float] = {}
        if isinstance(anchor, MultiAxisPolarAnchor) and anchor.axes:
            for ax in anchor.axes:
                axis_scores[ax.name] = scalar
            position = PositionVector.from_list([scalar] * len(anchor.axes))
        elif isinstance(anchor, PolarAnchor):
            axis_scores[anchor.axis_name] = scalar
            position = PositionVector.from_scalar(scalar)
        else:
            axis_scores["general_stance"] = scalar
            position = PositionVector.from_scalar(scalar)

        return StanceExtractionResult(
            position=position,
            scalar_stance=scalar,
            axis_scores=axis_scores,
            confidence=round(confidence, 3),
            primary_claims=[],
            backend_used="lexical",
            raw_text=text,
        )


# ---------------------------------------------------------------------------
# 2. Embedding-Based Semantic Projection Stance Extractor (OpenRouter)
# ---------------------------------------------------------------------------


class EmbeddingStanceExtractor(BaseStanceExtractor):
    """Semantic projection stance extractor using OpenRouter embeddings."""

    DEFAULT_ANCHOR = PolarAnchor(
        thesis_statement="Precision megalithic stonework exhibits non-standard tool kinematics and advanced machining.",
        antithesis_statement="Orthodox Bronze Age tools and manual techniques fully explain all ancient stonework.",
        axis_name="archaeological_kinematics",
    )

    def __init__(
        self,
        client: Optional[OpenRouterEmbeddingClient] = None,
        default_anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> None:
        self.client = client or OpenRouterEmbeddingClient()
        self.default_anchor = default_anchor or self.DEFAULT_ANCHOR

    @staticmethod
    def _cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
        min_dim = min(len(v1), len(v2))
        dot = sum(v1[i] * v2[i] for i in range(min_dim))
        mag1 = math.sqrt(sum(x * x for x in v1))
        mag2 = math.sqrt(sum(x * x for x in v2))
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
        return dot / (mag1 * mag2)

    def extract(
        self,
        text: str,
        anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> StanceExtractionResult:
        if not text or not text.strip():
            return StanceExtractionResult(
                position=PositionVector.from_scalar(0.0),
                scalar_stance=0.0,
                axis_scores={},
                confidence=0.0,
                primary_claims=[],
                backend_used="embedding",
                raw_text=text,
            )

        active_anchor = anchor or self.default_anchor

        # 1. Multi-Axis Semantic Projection
        if isinstance(active_anchor, MultiAxisPolarAnchor) and active_anchor.axes:
            texts_to_embed = [text]
            for ax in active_anchor.axes:
                texts_to_embed.append(ax.thesis_statement)
                texts_to_embed.append(ax.antithesis_statement)

            embeddings = self.client.get_batch_embeddings(texts_to_embed)
            text_emb = embeddings[0]

            axis_scores: Dict[str, float] = {}
            coords: List[float] = []
            confidences: List[float] = []

            for idx, ax in enumerate(active_anchor.axes):
                thesis_emb = embeddings[1 + idx * 2]
                antithesis_emb = embeddings[2 + idx * 2]

                sim_t = self._cosine_similarity(text_emb, thesis_emb)
                sim_a = self._cosine_similarity(text_emb, antithesis_emb)

                raw_proj = (sim_t - sim_a) * 5.0
                scalar_i = max(-1.0, min(1.0, round(raw_proj, 4)))
                axis_scores[ax.name] = scalar_i
                coords.append(scalar_i)
                confidences.append(round(min(1.0, max(0.2, (sim_t + sim_a))), 3))

            mean_scalar = coords[0] if coords else 0.0
            avg_conf = sum(confidences) / max(1, len(confidences))

            return StanceExtractionResult(
                position=PositionVector.from_list(coords),
                scalar_stance=mean_scalar,
                axis_scores=axis_scores,
                confidence=round(avg_conf, 3),
                primary_claims=[],
                backend_used=f"openrouter:{self.client.model}",
                raw_text=text,
            )

        # 2. Single-Axis Semantic Projection
        single_anchor: PolarAnchor
        if isinstance(active_anchor, PolarAnchor):
            single_anchor = active_anchor
        else:
            single_anchor = self.DEFAULT_ANCHOR

        texts_to_embed = [
            text,
            single_anchor.thesis_statement,
            single_anchor.antithesis_statement,
        ]
        embeddings = self.client.get_batch_embeddings(texts_to_embed)

        text_emb = embeddings[0]
        thesis_emb = embeddings[1]
        antithesis_emb = embeddings[2]

        sim_thesis = self._cosine_similarity(text_emb, thesis_emb)
        sim_antithesis = self._cosine_similarity(text_emb, antithesis_emb)

        raw_projection = (sim_thesis - sim_antithesis) * 5.0
        scalar = max(-1.0, min(1.0, round(raw_projection, 4)))
        confidence = round(min(1.0, max(0.2, (sim_thesis + sim_antithesis))), 3)

        return StanceExtractionResult(
            position=PositionVector.from_list(text_emb),
            scalar_stance=scalar,
            axis_scores={single_anchor.axis_name: scalar},
            confidence=confidence,
            primary_claims=[],
            backend_used=f"openrouter:{self.client.model}",
            raw_text=text,
        )


# ---------------------------------------------------------------------------
# 3. Composite Stance Extractor (Cascade: OpenRouter -> Lexical Fallback)
# ---------------------------------------------------------------------------


class CompositeStanceExtractor(BaseStanceExtractor):
    """Smart extractor that uses OpenRouter embeddings with automatic lexical fallback."""

    def __init__(
        self,
        embedding_extractor: Optional[EmbeddingStanceExtractor] = None,
        lexical_extractor: Optional[LexicalStanceExtractor] = None,
        prefer_lexical: bool = False,
    ) -> None:
        self.embedding_extractor = embedding_extractor
        self.lexical_extractor = lexical_extractor or LexicalStanceExtractor()
        self.prefer_lexical = prefer_lexical

    def extract(
        self,
        text: str,
        anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> StanceExtractionResult:
        if not self.prefer_lexical and self.embedding_extractor is not None:
            try:
                if self.embedding_extractor.client.api_key:
                    return self.embedding_extractor.extract(text, anchor=anchor)
            except Exception as e:
                logger.warning(
                    f"Embedding extraction failed or rate limited ({e}), falling back to lexical parser."
                )

        return self.lexical_extractor.extract(text, anchor=anchor)


# ---------------------------------------------------------------------------
# 4. Multi-Axis Stance Extractor with Weighted Stance & Multi-Tripwire Gate
# ---------------------------------------------------------------------------


class MultiAxisStanceResult(BaseModel):
    """Result of evaluating an utterance across multiple calibrated epistemic axes."""

    position: PositionVector
    axis_scores: Dict[str, float] = Field(
        default_factory=dict, description="Individual normalized stance scores per axis in [-1.0, 1.0]."
    )
    axis_weights: Dict[str, float] = Field(
        default_factory=dict, description="Normalized weights per axis summing to 1.0."
    )
    weighted_total_stance: float = Field(
        description="Weighted combined stance scalar: s_total = sum(w_i * s_i)."
    )
    per_axis_tripwire_tripped: Dict[str, bool] = Field(
        default_factory=dict, description="Flags whether individual axis score exceeded per_axis_threshold."
    )
    global_tripwire_tripped: bool = Field(
        default=False, description="Flags whether weighted total stance exceeded global_threshold."
    )
    is_any_tripwire_tripped: bool = Field(
        default=False, description="True if either global or any per-axis tripwire is tripped."
    )
    per_axis_threshold: float = 0.50
    global_threshold: float = 0.40
    raw_text: str = ""
    backend_used: str = "multi_axis"


class MultiAxisStanceExtractor(BaseStanceExtractor):
    """Multi-axis stance extractor supporting calibrated AxisProfiles, dynamic weighting, and dual tripwires."""

    def __init__(
        self,
        profiles: Optional[Sequence[Any]] = None,
        multi_anchor: Optional[MultiAxisPolarAnchor] = None,
        weights: Optional[Dict[str, float]] = None,
        base_extractor: Optional[BaseStanceExtractor] = None,
        embedding_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
        per_axis_threshold: float = 0.50,
        global_threshold: float = 0.40,
    ) -> None:
        self.profiles = list(profiles) if profiles else []
        self.multi_anchor = multi_anchor or (
            MultiAxisPolarAnchor.default_tri_axial_anchor() if not self.profiles else None
        )
        self.weights = weights or {}
        self.base_extractor = base_extractor or CompositeStanceExtractor()
        self.embedding_fn = embedding_fn
        self.per_axis_threshold = per_axis_threshold
        self.global_threshold = global_threshold

    def compute_stance(
        self,
        utterance: str,
        axes: Optional[Sequence[Any]] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> MultiAxisStanceResult:
        """Project an utterance across all active axes and compute weighted combination."""
        active_axes = axes if axes is not None else (self.profiles or (self.multi_anchor.axes if self.multi_anchor else []))
        raw_weights = weights if weights is not None else self.weights

        if not utterance or not utterance.strip():
            return MultiAxisStanceResult(
                position=PositionVector.from_scalar(0.0),
                axis_scores={},
                axis_weights={},
                weighted_total_stance=0.0,
                per_axis_tripwire_tripped={},
                global_tripwire_tripped=False,
                is_any_tripwire_tripped=False,
                per_axis_threshold=self.per_axis_threshold,
                global_threshold=self.global_threshold,
                raw_text=utterance,
            )

        axis_scores: Dict[str, float] = {}
        coords: List[float] = []

        # 1. Project across each axis
        for ax in active_axes:
            # Calibrated AxisProfile with pre-computed unit vector and domain center
            if hasattr(ax, "unit_axis_vector") and ax.unit_axis_vector and hasattr(ax, "domain_center"):
                axis_id = getattr(ax, "axis_id", "custom_axis")
                optimal_k = getattr(ax, "optimal_k", 5.0)

                emb = None
                if self.embedding_fn is not None:
                    try:
                        emb = self.embedding_fn([utterance])[0]
                    except Exception:
                        pass
                elif isinstance(self.base_extractor, CompositeStanceExtractor) and self.base_extractor.embedding_extractor:
                    client = self.base_extractor.embedding_extractor.client
                    if client.api_key:
                        try:
                            emb = client.get_embedding(utterance)
                        except Exception:
                            pass

                if emb is not None:
                    # Mean-center
                    centered_emb = [e - c for e, c in zip(emb, ax.domain_center)]
                    # Dot product with unit axis vector
                    dot = sum(e * v for e, v in zip(centered_emb, ax.unit_axis_vector))
                    scalar = max(-1.0, min(1.0, round(dot * optimal_k, 4)))
                else:
                    lex_res = LexicalStanceExtractor().extract(utterance)
                    scalar = lex_res.scalar_stance

                axis_scores[axis_id] = scalar
                coords.append(scalar)
            elif isinstance(ax, PolarAxis):
                single_anchor = PolarAnchor(
                    thesis_statement=ax.thesis_statement,
                    antithesis_statement=ax.antithesis_statement,
                    axis_name=ax.name,
                )
                res = self.base_extractor.extract(utterance, anchor=single_anchor)
                axis_scores[ax.name] = res.scalar_stance
                coords.append(res.scalar_stance)
            elif hasattr(ax, "name"):
                axis_name = getattr(ax, "name")
                res = self.base_extractor.extract(utterance)
                axis_scores[axis_name] = res.scalar_stance
                coords.append(res.scalar_stance)

        # 2. Normalize weights
        axis_names = list(axis_scores.keys())
        normalized_weights: Dict[str, float] = {}

        if not axis_names:
            return MultiAxisStanceResult(
                position=PositionVector.from_scalar(0.0),
                axis_scores={},
                axis_weights={},
                weighted_total_stance=0.0,
                per_axis_tripwire_tripped={},
                global_tripwire_tripped=False,
                is_any_tripwire_tripped=False,
                raw_text=utterance,
            )

        total_weight_sum = sum(raw_weights.get(name, 1.0) for name in axis_names)
        if total_weight_sum <= 0.0:
            total_weight_sum = float(len(axis_names))

        for name in axis_names:
            w = raw_weights.get(name, 1.0) / total_weight_sum
            normalized_weights[name] = round(w, 4)

        # 3. Compute weighted total stance
        weighted_total = sum(axis_scores[name] * normalized_weights[name] for name in axis_names)
        weighted_total = max(-1.0, min(1.0, round(weighted_total, 4)))

        # 4. Tripwire evaluations
        per_axis_tripwire: Dict[str, bool] = {}
        for name, score in axis_scores.items():
            per_axis_tripwire[name] = bool(score >= self.per_axis_threshold)

        global_tripwire = bool(weighted_total >= self.global_threshold)
        is_any_tripped = global_tripwire or any(per_axis_tripwire.values())

        return MultiAxisStanceResult(
            position=PositionVector.from_list(coords if coords else [weighted_total]),
            axis_scores=axis_scores,
            axis_weights=normalized_weights,
            weighted_total_stance=weighted_total,
            per_axis_tripwire_tripped=per_axis_tripwire,
            global_tripwire_tripped=global_tripwire,
            is_any_tripwire_tripped=is_any_tripped,
            per_axis_threshold=self.per_axis_threshold,
            global_threshold=self.global_threshold,
            raw_text=utterance,
        )

    def extract(
        self,
        text: str,
        anchor: Optional[Union[PolarAnchor, MultiAxisPolarAnchor]] = None,
    ) -> StanceExtractionResult:
        """Compatibility adapter implementing BaseStanceExtractor."""
        res = self.compute_stance(text)
        return StanceExtractionResult(
            position=res.position,
            scalar_stance=res.weighted_total_stance,
            axis_scores=res.axis_scores,
            confidence=0.9,
            primary_claims=[],
            backend_used="multi_axis",
            raw_text=text,
        )
