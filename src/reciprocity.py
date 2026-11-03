"""A conservative, role-symmetric review layer for reciprocal reasoning.

This is an observational evaluator. It does not decide whether an argument is
true, independently verify sources, or block responses. Evidence findings must
come from separately inspected work; a DOI-shaped string is not verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class Decision(str, Enum):
    REVISE = "revise"
    RETAIN = "retain"


class Finding(str, Enum):
    SUPPORTS_REVISION = "supports_revision"
    SUPPORTS_RETENTION = "supports_retention"
    INCONCLUSIVE = "inconclusive"


class Verification(str, Enum):
    UNREVIEWED = "unreviewed"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Outcome(str, Enum):
    DIFFERENT_PROPOSITION = "different_proposition"
    UNRESOLVED = "unresolved"
    JUSTIFIED_REVISION = "justified_revision"
    UNJUSTIFIED_REVISION = "unjustified_revision"
    JUSTIFIED_RETENTION = "justified_retention"
    UNJUSTIFIED_RETENTION = "unjustified_retention"


@dataclass(frozen=True)
class Proposition:
    """A question and its scope, with a stable identifier.

    Frame comparison is deliberately exact. A paraphrase, changed scope, or
    reused identifier requires clarification or an explicit reconciliation;
    this module must not silently declare semantic equivalence.
    """

    claim_id: str
    question: str
    scope: str

    def __post_init__(self) -> None:
        if not all(v.strip() for v in (self.claim_id, self.question, self.scope)):
            raise ValueError("Proposition requires nonempty claim_id, question and scope")

    def matches(self, other: "Proposition") -> bool:
        return (
            self.claim_id == other.claim_id
            and self.question.strip() == other.question.strip()
            and self.scope.strip() == other.scope.strip()
        )


@dataclass(frozen=True)
class EvidenceReview:
    """An external reviewer's finding, not proof of objective truth.

    VERIFIED means someone supplied a named review with a source and
    rationale. This module cannot authenticate that reviewer or source.
    Applications must validate those attestations before relying on them.
    """

    evidence_id: str
    claim_id: str
    finding: Finding
    verification: Verification = Verification.UNREVIEWED
    source_ref: str = ""
    reviewer: str = ""
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.claim_id.strip():
            raise ValueError("Evidence review requires evidence_id and claim_id")
        if self.verification is Verification.VERIFIED and not all(
            v.strip() for v in (self.source_ref, self.reviewer, self.rationale)
        ):
            raise ValueError(
                "Verified evidence requires source_ref, reviewer, and rationale"
            )


@dataclass(frozen=True)
class ReciprocalEvent:
    """One participant's decision about one proposition.

    participant_id is intentionally metadata, not an evidentiary input.
    """

    participant_id: str
    before: Proposition
    after: Proposition
    decision: Decision
    evidence: Sequence[EvidenceReview] = ()

    def __post_init__(self) -> None:
        if not self.participant_id.strip():
            raise ValueError("participant_id must not be blank")


@dataclass(frozen=True)
class ReciprocalReport:
    outcome: Outcome
    participant_id: str
    claim_id: str
    considered_evidence: tuple[str, ...]
    excluded_evidence: tuple[str, ...]
    explanation: str


def review_reciprocal_event(event: ReciprocalEvent) -> ReciprocalReport:
    """Classify revision/retention using supplied external evidence reviews.

    No verified findings, competing verified findings, or a proposition mismatch
    mean 'unresolved', never assumed capitulation. The only asymmetry in the
    judgment is the evidence for revision versus retention; a participant
    label has no effect on the outcome.

    The result is conditional on trustworthy external review attestations.
    """

    if not event.before.matches(event.after):
        return ReciprocalReport(
            outcome=Outcome.DIFFERENT_PROPOSITION,
            participant_id=event.participant_id,
            claim_id=event.before.claim_id,
            considered_evidence=(),
            excluded_evidence=tuple(e.evidence_id for e in event.evidence),
            explanation="Question, scope, or claim identifier changed; reconcile the claim first.",
        )

    considered = tuple(
        e for e in event.evidence
        if e.claim_id == event.before.claim_id and e.verification is Verification.VERIFIED
    )
    excluded = tuple(e.evidence_id for e in event.evidence if e not in considered)
    findings = {e.finding for e in considered if e.finding is not Finding.INCONCLUSIVE}
    trace = tuple(e.evidence_id for e in considered)

    if not findings:
        outcome = Outcome.UNRESOLVED
        reason = "No decisive, externally attested evidence is available."
    elif len(findings) > 1:
        outcome = Outcome.UNRESOLVED
        reason = "Verified findings conflict; further review is required."
    else:
        supports_revision = Finding.SUPPORTS_REVISION in findings
        if event.decision is Decision.REVISE:
            outcome = (
                Outcome.JUSTIFIED_REVISION if supports_revision
                else Outcome.UNJUSTIFIED_REVISION
            )
        else:
            outcome = (
                Outcome.UNJUSTIFIED_RETENTION if supports_revision
                else Outcome.JUSTIFIED_RETENTION
            )
        reason = (
            "Classification is conditional on independently validating the "
            "supplied evidence assessments; participant identity is not a factor."
        )

    return ReciprocalReport(
        outcome=outcome,
        participant_id=event.participant_id,
        claim_id=event.before.claim_id,
        considered_evidence=trace,
        excluded_evidence=excluded,
        explanation=reason,
    )
