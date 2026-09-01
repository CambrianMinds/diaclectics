import pytest
from pathlib import Path
from src.calibration.codebase_discoverer import EpistemicCodebaseDiscoverer, DiscoveredInvariant
from src.verifier.search_verifier import SearchVerifier, SearchResult, AcademicPaper



class MockSearchVerifier(SearchVerifier):
    """Mock search verifier for deterministic triangulation tests."""

    def search(self, query: str, limit: int = 3) -> SearchResult:
        paper = AcademicPaper(
            title="Thermodynamics of Cutting Tool Wear and Feed Rate Bounds",
            doi="10.1016/j.triboint.2021.107000",
            authors=["J. Smith", "A. Taylor"],
            publication_year=2021,
            journal_or_venue="Tribology International",
            citation_count=45,
            abstract="Taylor tool life equations govern wear rate across feeds."
        )
        return SearchResult(query=query, papers_found=[paper], is_grounded=True)



def test_codebase_discoverer_scans_file(tmp_path: Path) -> None:
    sample_file = tmp_path / "kinematics_test.py"
    sample_file.write_text(
        '"""Kinematics module.\n\nFeed rate and cutting speed bounds are critical.\n"""\n'
        'def compute_spindle(feed_rate: float):\n'
        '    """Calculates spindle speed based on Taylor tool life equations."""\n'
        '    assert feed_rate > 0, "feed rate must be strictly positive"\n'
        '    return feed_rate * 1.5\n',
        encoding="utf-8"
    )

    discoverer = EpistemicCodebaseDiscoverer(search_verifier=MockSearchVerifier())
    invariants = discoverer.scan_python_file(sample_file)

    assert len(invariants) >= 2
    assert any(inv.domain == "kinematics" for inv in invariants)


def test_codebase_discoverer_triangulates_and_creates_seed(tmp_path: Path) -> None:
    sample_file = tmp_path / "memory_safety_test.py"
    sample_file.write_text(
        'def enforce_borrow_checker():\n'
        '    """Enforces affine type and data race safety."""\n'
        '    pass\n',
        encoding="utf-8"
    )

    discoverer = EpistemicCodebaseDiscoverer(search_verifier=MockSearchVerifier())
    invariants = discoverer.scan_python_file(sample_file)
    assert len(invariants) > 0

    triangulated = discoverer.triangulate_invariant(invariants[0])
    assert len(triangulated.literature_citations) > 0
    assert "DOI" in triangulated.synthesized_positive_anchor or "literature" in triangulated.synthesized_positive_anchor

    seed_model = discoverer.create_calibrated_seed_profile("test_memory_safety", invariants)
    assert seed_model.axis_id == "test_memory_safety"
    assert len(seed_model.seeds) >= 6
    assert any(s.tier == "positive" for s in seed_model.seeds)
    assert any(s.tier == "negative" for s in seed_model.seeds)

