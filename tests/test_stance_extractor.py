"""Tests for Automated Stance Extractor, Rate Limiting, Caching, and Semantic Projections."""

import pytest
import time

from src.tracker.stance_extractor import (
    CompositeStanceExtractor,
    EmbeddingCache,
    EmbeddingRateLimiter,
    EmbeddingStanceExtractor,
    LexicalStanceExtractor,
    OpenRouterEmbeddingClient,
    PolarAnchor,
    StanceExtractionResult,
)


def test_embedding_cache():
    cache = EmbeddingCache(cache_file=None)
    assert cache.size() == 0
    cache.set("test statement", "test_model", [0.1, 0.2, 0.3])
    assert cache.size() == 1
    hit = cache.get("test statement", "test_model")
    assert hit == [0.1, 0.2, 0.3]
    miss = cache.get("other statement", "test_model")
    assert miss is None


def test_embedding_rate_limiter_spacing():
    # Test minimal interval enforcement
    limiter = EmbeddingRateLimiter(max_requests_per_minute=60, min_interval_seconds=0.05)
    t0 = time.time()
    limiter.acquire()
    limiter.acquire()
    t1 = time.time()
    assert t1 - t0 >= 0.04


def test_lexical_stance_extractor_affirmation():
    extractor = LexicalStanceExtractor()
    res = extractor.extract("I completely agree and confirm that this hypothesis is validated and proven.")
    assert res.scalar_stance > 0.5
    assert res.confidence > 0.5
    assert res.backend_used == "lexical"


def test_lexical_stance_extractor_negation():
    extractor = LexicalStanceExtractor()
    res = extractor.extract("I disagree and reject this flawed premise; it is clearly refuted.")
    assert res.scalar_stance < -0.5
    assert res.backend_used == "lexical"


def test_lexical_stance_extractor_hedging():
    extractor = LexicalStanceExtractor()
    res = extractor.extract("Perhaps maybe it is possibly true, but inconclusive.")
    assert abs(res.scalar_stance) <= 0.5


def test_semantic_projection_mock_vectors():
    # Test semantic projection logic with predefined orthogonal and aligned vectors
    extractor = EmbeddingStanceExtractor()
    v_text = [1.0, 0.0]
    v_thesis = [1.0, 0.0]
    v_antithesis = [-1.0, 0.0]

    sim_thesis = extractor._cosine_similarity(v_text, v_thesis)
    sim_anti = extractor._cosine_similarity(v_text, v_antithesis)
    assert pytest.approx(sim_thesis) == 1.0
    assert pytest.approx(sim_anti) == -1.0


def test_composite_stance_extractor_fallback():
    # Without API key, composite extractor falls back gracefully to lexical
    client = OpenRouterEmbeddingClient(api_key="")
    embed_extractor = EmbeddingStanceExtractor(client=client)
    composite = CompositeStanceExtractor(
        embedding_extractor=embed_extractor,
        lexical_extractor=LexicalStanceExtractor(),
    )

    res = composite.extract("I agree and confirm this is optimal.")
    assert res.backend_used == "lexical"
    assert res.scalar_stance > 0.0
