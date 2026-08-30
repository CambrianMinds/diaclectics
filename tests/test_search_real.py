"""Tests for Real-Time Scientific Literature Search Engine (OpenAlex, Crossref, Wikipedia)."""

from src.verifier.search_verifier import AcademicPaper, SearchResult, SearchVerifier


def test_academic_paper_model():
    paper = AcademicPaper(
        title="Impact Geochemistry of the Younger Dryas Boundary",
        doi="https://doi.org/10.1038/srep44031",
        authors=["Moore, C. R.", "West, A."],
        publication_year=2017,
        journal_or_venue="Scientific Reports",
        abstract="Widespread platinum anomaly documented at the Younger Dryas onset in sedimentary sequences.",
        citation_count=85,
        source_api="OpenAlex",
    )
    assert paper.citation_count == 85
    assert "Moore" in paper.authors[0]


def test_search_result_literature_formatting():
    paper = AcademicPaper(
        title="Petrie Core #7 Metrological Survey",
        doi="https://doi.org/10.1000/182",
        authors=["Petrie, W. M. F."],
        publication_year=1883,
        abstract="Granite core with 0.100 inch feed rate per revolution.",
        citation_count=120,
    )
    res = SearchResult(
        query="Petrie core #7",
        is_grounded=True,
        papers_found=[paper],
        snippets=["[Abu Rawash]: Granite saw cuts."],
        sources=["https://doi.org/10.1000/182"],
    )

    formatted = res.format_literature_context()
    assert "PEER-REVIEWED SCIENTIFIC LITERATURE FOUND" in formatted
    assert "Petrie Core #7 Metrological Survey" in formatted
    assert "DOI: https://doi.org/10.1000/182" in formatted
    assert "Granite core with 0.100 inch feed rate" in formatted


def test_search_verifier_caching(tmp_path):
    cache_file = tmp_path / "test_search_cache.json"
    verifier = SearchVerifier(cache_file=str(cache_file))

    # Search Wikipedia / OpenAlex query
    res = verifier.search("Antideficiency Act 31 U.S.C. 1341", max_results=2)
    assert isinstance(res, SearchResult)
    assert res.is_grounded is True
    assert cache_file.exists()

    # Second call should be from cache
    res2 = verifier.search("Antideficiency Act 31 U.S.C. 1341", max_results=2)
    assert res2.cached is True
