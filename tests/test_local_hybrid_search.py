"""Tests for Zero-API-Cost Local Hybrid Search (SQLite FTS5 + Dense Vectors)."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.storage.db import init_db
from src.verifier.local_index import LocalKnowledgeIndex, LocalVectorizer
from src.verifier.search_verifier import AcademicPaper, SearchVerifier


@pytest.fixture
def local_index(tmp_path: Path) -> LocalKnowledgeIndex:
    db_path = str(tmp_path / "test_local_corpus.db")
    init_db(db_path)
    return LocalKnowledgeIndex(db_path=db_path)


def test_local_vectorizer_normalization() -> None:
    """Verify LocalVectorizer produces normalized vectors and handles empty text."""
    vectorizer = LocalVectorizer(dim=384)

    # Empty text
    empty_vec = vectorizer.embed_text("")
    assert len(empty_vec) == 384
    assert sum(empty_vec) == 0.0

    # Normal text
    vec = vectorizer.embed_text("Kinematic cutting forces and stone striations.")
    assert len(vec) == 384
    # Check unit norm: sqrt(sum(v^2)) == 1.0
    norm = sum(v * v for v in vec) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-3)


def test_local_index_ingestion_and_fts_search(local_index: LocalKnowledgeIndex) -> None:
    """Verify document ingestion and FTS5 keyword retrieval."""
    local_index.index_document(
        doc_id="doc_aerospace_1",
        title="Aerospace Kinematics & Orbital Mechanics",
        content="Conservation of angular momentum dictates orbital precession in non-spherical gravitational fields.",
        doi="10.1016/j.actaastro.2023.01.001",
        authors=["J. Doe", "A. Smith"],
        year=2023,
        venue="Acta Astronautica",
        citation_count=42,
    )
    local_index.index_document(
        doc_id="doc_archaeology_2",
        title="Bronze Age Tooling and Megalithic Extraction",
        content="Copper saws with quartz sand abrasive slurry account for granite saw slots at Giza.",
        doi="10.1016/j.jas.2021.05.004",
        authors=["M. Lehner"],
        year=2021,
        venue="Journal of Archaeological Science",
        citation_count=85,
    )

    # Query matching aerospace
    results = local_index.search("angular momentum orbital precession", top_k=2)
    assert len(results) > 0
    assert results[0].title == "Aerospace Kinematics & Orbital Mechanics"
    assert results[0].doi == "10.1016/j.actaastro.2023.01.001"
    assert results[0].source_api == "LocalHybridIndex"

    # Query matching archaeology
    arch_results = local_index.search("copper saws quartz abrasive granite", top_k=2)
    assert len(arch_results) > 0
    assert arch_results[0].title == "Bronze Age Tooling and Megalithic Extraction"


def test_local_index_paper_indexing_and_vector_match(local_index: LocalKnowledgeIndex) -> None:
    """Verify indexing AcademicPaper objects and vector similarity ranking."""
    paper = AcademicPaper(
        title="Empirical Stance Dynamics in LLMs",
        doi="10.48550/arXiv.2405.00123",
        authors=["Epistemic AI Group"],
        publication_year=2024,
        journal_or_venue="arXiv AI Safety",
        abstract="We measure epistemic drift and sycophantic capitulation using multi-axis geometric projections.",
        citation_count=19,
    )
    local_index.index_paper(paper)

    results = local_index.search("epistemic drift geometric projections", top_k=1)
    assert len(results) == 1
    assert results[0].title == "Empirical Stance Dynamics in LLMs"
    assert results[0].doi == "10.48550/arXiv.2405.00123"


def test_local_index_directory_scanning(local_index: LocalKnowledgeIndex, tmp_path: Path) -> None:
    """Verify scanning and indexing markdown files in a directory."""
    docs_dir = tmp_path / "axioms"
    docs_dir.mkdir()

    (docs_dir / "thermodynamics.md").write_text(
        "# Second Law of Thermodynamics\nEntropy in an isolated system never decreases over time.",
        encoding="utf-8",
    )
    (docs_dir / "relativity.md").write_text(
        "# General Relativity\nSpacetime curvature is directly proportional to energy-momentum tensor.",
        encoding="utf-8",
    )

    count = local_index.index_directory(docs_dir, glob_pattern="*.md")
    assert count == 2

    results = local_index.search("entropy isolated system", top_k=1)
    assert len(results) == 1
    assert "Thermodynamics" in results[0].title


def test_search_verifier_offline_mode_integration(tmp_path: Path) -> None:
    """Verify SearchVerifier uses LocalKnowledgeIndex in offline mode with zero network calls."""
    db_path = str(tmp_path / "offline_db.db")
    init_db(db_path)
    local_idx = LocalKnowledgeIndex(db_path=db_path)

    local_idx.index_document(
        doc_id="quantum_1",
        title="Quantum Decoherence and Epistemic Measurement",
        content="Wavefunction collapse under environmental interaction prevents macroscopic superposition.",
        doi="10.1103/PhysRevA.99.012101",
        authors=["W. Zurek"],
        year=2019,
        venue="Physical Review A",
        citation_count=320,
    )

    verifier = SearchVerifier(
        cache_file=str(tmp_path / "cache.json"),
        local_index=local_idx,
        offline_mode=True,
    )

    res = verifier.search("wavefunction collapse macroscopic superposition", max_results=1)
    assert res.is_grounded is True
    assert len(res.papers_found) == 1
    assert res.papers_found[0].title == "Quantum Decoherence and Epistemic Measurement"
    assert res.verified_doi_count == 1
    assert "10.1103/PhysRevA.99.012101" in res.sources
