"""Tests for Active Epistemic Verifier Subsystem."""

import pytest

from src.verifier.claim_extractor import ClaimExtractor, FalsifiableClaim
from src.verifier.epistemic_validator import EpistemicValidator
from src.verifier.reasoning_judge import EpistemicEvaluation, EpistemicReasoningJudge
from src.verifier.search_verifier import SearchResult, SearchVerifier


def test_claim_extractor_kinematics():
    extractor = ClaimExtractor()
    text = (
        "The witness mark at Abu Rawash has a convex circular saw cut with radius of curvature "
        "exceeding 8 feet. The feed rate of core #7 is 0.100 inches per revolution in granite."
    )
    extracted = extractor.extract_claims(text)
    assert extracted.total_claims >= 2
    types = [c.claim_type for c in extracted.claims]
    assert "PHYSICAL_KINEMATIC" in types
    units = [u for c in extracted.claims for u in c.quantities_or_units]
    assert any("inches" in u or "feet" in u for u in units)


def test_claim_extractor_stratigraphy_and_statute():
    extractor = ClaimExtractor()
    text = (
        "The Black Mat layer across 4 continents contains platinum spikes at 12,800 BP. "
        "Under the Anti-Deficiency Act and War Powers Resolution, executive authority is constrained."
    )
    extracted = extractor.extract_claims(text)
    assert extracted.total_claims >= 2
    types = [c.claim_type for c in extracted.claims]
    assert "STRATIGRAPHIC_CHRONOLOGY" in types
    assert "STATUTORY_LEGAL" in types


def test_search_verifier_caching():
    verifier = SearchVerifier(cache_file=None)
    res = verifier.search("Flinders Petrie granite core 7")
    assert res.query == "Flinders Petrie granite core 7"
    assert isinstance(res.snippets, list)


def test_reasoning_judge_deterministic_evaluation():
    judge = EpistemicReasoningJudge(api_key="")  # Force deterministic offline evaluation
    claim = FalsifiableClaim(
        claim_text="The circular saw mark at Abu Rawash exhibits convex curvature.",
        claim_type="PHYSICAL_KINEMATIC",
        quantities_or_units=["8 feet"],
    )
    eval_res = judge.evaluate_claim(claim)
    assert eval_res.is_valid_constraint is True
    assert eval_res.asymmetric_weight >= 3.0
    assert "Material kinematics" in eval_res.epistemic_rationale


def test_epistemic_validator_end_to_end():
    validator = EpistemicValidator(
        search_verifier=SearchVerifier(cache_file=None),
        reasoning_judge=EpistemicReasoningJudge(api_key=""),
    )
    text = (
        "Witness marks left in the granite off-cuts at Abu Rawash show circular saw cutting lines. "
        "Petrie documented core #7 with a feed rate of 0.100 inches per revolution."
    )
    report = validator.validate_utterance(text)
    assert report.total_claims_evaluated >= 2
    assert report.net_asymmetric_weight > 4.0
    assert report.has_valid_constraints is True
    assert "Active Epistemic Validation" in report.epistemic_summary_why
    assert "Weight:" in report.epistemic_summary_why
