"""Acceptance tests for the non-blocking reciprocal evaluation layer."""

from dataclasses import replace

import pytest

from src.reciprocity import (
    Decision,
    EvidenceReview,
    Finding,
    Outcome,
    Proposition,
    ReciprocalEvent,
    Verification,
    review_reciprocal_event,
)


FRAME = Proposition(
    claim_id="circularity",
    question="Does this image feature satisfy the stated circularity constraint?",
    scope="Specified ROI, camera model, and uncertainty",
)


def assessed(finding, verification=Verification.VERIFIED, claim_id="circularity"):
    return EvidenceReview(
        evidence_id="e1",
        claim_id=claim_id,
        finding=finding,
        verification=verification,
        source_ref="analysis/measurement.csv" if verification is Verification.VERIFIED else "",
        reviewer="independent reviewer" if verification is Verification.VERIFIED else "",
        rationale="Checked the stated constraint against measurements"
        if verification is Verification.VERIFIED else "",
    )


@pytest.mark.parametrize(
    "decision,finding,expected",
    [
        (Decision.REVISE, Finding.SUPPORTS_REVISION, Outcome.JUSTIFIED_REVISION),
        (Decision.REVISE, Finding.SUPPORTS_RETENTION, Outcome.UNJUSTIFIED_REVISION),
        (Decision.RETAIN, Finding.SUPPORTS_RETENTION, Outcome.JUSTIFIED_RETENTION),
        (Decision.RETAIN, Finding.SUPPORTS_REVISION, Outcome.UNJUSTIFIED_RETENTION),
    ],
)
def test_evidence_treats_human_and_ai_identically(decision, finding, expected):
    evidence = (assessed(finding),)
    for participant in ("human", "ai", "unknown-agent"):
        result = review_reciprocal_event(
            ReciprocalEvent(participant, FRAME, FRAME, decision, evidence)
        )
        assert result.outcome is expected
        assert result.considered_evidence == ("e1",)


@pytest.mark.parametrize(
    "after",
    [
        Proposition("another", FRAME.question, FRAME.scope),
        Proposition(FRAME.claim_id, "Does a different claim hold?", FRAME.scope),
        Proposition(FRAME.claim_id, FRAME.question, "Different observation window"),
    ],
)
def test_claim_identifier_question_and_scope_must_all_match(after):
    event = ReciprocalEvent("human", FRAME, after, Decision.REVISE, (assessed(Finding.SUPPORTS_REVISION),))
    result = review_reciprocal_event(event)
    assert result.outcome is Outcome.DIFFERENT_PROPOSITION
    assert result.considered_evidence == ()


def test_unchecked_doi_or_jargon_is_not_verified_evidence():
    alleged = EvidenceReview(
        evidence_id="looks-cited",
        claim_id=FRAME.claim_id,
        finding=Finding.SUPPORTS_REVISION,
        source_ref="10.0000/looks-like-a-doi",
        verification=Verification.UNREVIEWED,
    )
    result = review_reciprocal_event(
        ReciprocalEvent("ai", FRAME, FRAME, Decision.REVISE, (alleged,))
    )
    assert result.outcome is Outcome.UNRESOLVED
    assert result.excluded_evidence == ("looks-cited",)


def test_claiming_verification_requires_attributed_review():
    with pytest.raises(ValueError, match="source_ref"):
        EvidenceReview(
            evidence_id="fabricated",
            claim_id=FRAME.claim_id,
            finding=Finding.SUPPORTS_REVISION,
            verification=Verification.VERIFIED,
        )


def test_conflicting_review_results_remain_unresolved():
    evidence = (
        assessed(Finding.SUPPORTS_REVISION),
        replace(assessed(Finding.SUPPORTS_RETENTION), evidence_id="e2"),
    )
    result = review_reciprocal_event(
        ReciprocalEvent("human", FRAME, FRAME, Decision.RETAIN, evidence)
    )
    assert result.outcome is Outcome.UNRESOLVED
    assert result.considered_evidence == ("e1", "e2")


def test_evidence_for_another_claim_must_not_cross_contaminate():
    other = assessed(Finding.SUPPORTS_REVISION, claim_id="unrelated")
    result = review_reciprocal_event(
        ReciprocalEvent("ai", FRAME, FRAME, Decision.REVISE, (other,))
    )
    assert result.outcome is Outcome.UNRESOLVED
    assert result.excluded_evidence == ("e1",)


def test_rejected_evidence_is_not_counted():
    rejected = assessed(Finding.SUPPORTS_REVISION, verification=Verification.REJECTED)
    result = review_reciprocal_event(
        ReciprocalEvent("human", FRAME, FRAME, Decision.REVISE, (rejected,))
    )
    assert result.outcome is Outcome.UNRESOLVED


def test_calculation_can_support_revision_without_a_citation():
    calculation = EvidenceReview(
        evidence_id="proof-check",
        claim_id=FRAME.claim_id,
        finding=Finding.SUPPORTS_REVISION,
        verification=Verification.VERIFIED,
        source_ref="reproduced derivation in notebook cell 7",
        reviewer="separate symbolic check",
        rationale="Independently recomputed both sides and found an arithmetic error",
    )
    result = review_reciprocal_event(
        ReciprocalEvent("human", FRAME, FRAME, Decision.REVISE, (calculation,))
    )
    assert result.outcome is Outcome.JUSTIFIED_REVISION


def test_untested_evidence_never_makes_persistence_a_failure():
    result = review_reciprocal_event(
        ReciprocalEvent("ai", FRAME, FRAME, Decision.RETAIN)
    )
    assert result.outcome is Outcome.UNRESOLVED


def test_invalid_empty_proposition_is_rejected():
    with pytest.raises(ValueError):
        Proposition("some-id", " ", "a scope")


def test_event_rejects_raw_string_decisions():
    with pytest.raises(TypeError, match="Decision"):
        ReciprocalEvent("human", FRAME, FRAME, "revise")


def test_evidence_rejects_raw_string_status():
    with pytest.raises(TypeError, match="enum"):
        EvidenceReview(
            evidence_id="e3",
            claim_id=FRAME.claim_id,
            finding=Finding.SUPPORTS_REVISION,
            verification="verified",
        )


def test_engine_entrypoint_is_observational():
    from src.engine import DialecticalEngine

    engine = DialecticalEngine()
    event = ReciprocalEvent(
        "ai", FRAME, FRAME, Decision.REVISE, (assessed(Finding.SUPPORTS_REVISION),)
    )
    result = engine.review_reciprocal_event(event)
    assert result.outcome is Outcome.JUSTIFIED_REVISION
    assert engine.tracker.history == []
