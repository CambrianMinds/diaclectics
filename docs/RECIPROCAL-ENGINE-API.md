# Reciprocal Principle Engine: First Executable Increment

**Status:** Opt-in, observational Python API. No pre-emission enforcement.  
**Implementation:** [src/reciprocity.py](../src/reciprocity.py)  
**Tests:** [tests/test_reciprocity.py](../tests/test_reciprocity.py)  
**Foundation:** [Blarf Schnakkit Krakkit, v1.0](foundations/Blarf-Schnakkit-Krakkit-Foundational-Conditions-v1.0.md)

## What this increment does

It offers a conservative, deterministic interface for:
- proposition fidelity (same identifier, same question, same scope);
- identical treatment of human, AI, and other participant identities;
- classification of revision or retention against supplied evidence reviews;
- unresolved outcomes for unreviewed, conflicting, inconclusive, or unrelated evidence.

It does NOT independently authenticate sources, prove a calculation, infer semantic equivalence between paraphrases, or guarantee alignment. The caller remains responsible for independent review. A supplied Verification.ATTESTED value asserts that someone conducted a review; **it is not authenticated by the library**.

The module is separate from existing stance tracking and interception. DialecticalEngine.review_reciprocal_event is deliberately non-blocking. Existing output gate behavior has NOT changed.

## Usage

The example below supplies an attributed external review. Its validity must be independently checked by the application using the result.

~~~python
from src.engine import DialecticalEngine
from src.reciprocity import (
    Decision, EvidenceReview, Finding, Proposition, ReciprocalEvent, Verification
)

question = Proposition(
    claim_id="claim-1",
    question="Does the supplied calculation hold?",
    scope="The exact inputs and arithmetic in the submitted notebook",
)
checked = EvidenceReview(
    evidence_id="check-1",
    claim_id="claim-1",
    finding=Finding.SUPPORTS_REVISION,
    verification=Verification.ATTESTED,
    source_ref="notebook/cell-7",
    reviewer="independent re-computation",
    rationale="The recomputed sum contradicts the original result",
)
event = ReciprocalEvent(
    participant_id="human", before=question, after=question,
    decision=Decision.REVISE, evidence=(checked,)
)
report = DialecticalEngine().review_reciprocal_event(event)
print(report.outcome.value)  # justified_revision, conditional on reviewer validity
~~~

Change participant_id from human to ai, holding the evidence and event fixed: the classification is unchanged.

## Why exact proposition comparison?

Declaring that a paraphrase or changed scope expresses the same proposition requires a separate justification. For now the software returns DIFFERENT_PROPOSITION when the identifier, question, or scope changes. This means **not yet reconciled**, not necessarily semantically unrelated. A future workflow should support explicit mutual reconciliation.

## Conditional review outcomes

| Participant decision | Externally reviewed finding | Outcome |
| --- | --- | --- |
| Revise | Supports revision | JUSTIFIED_REVISION |
| Revise | Supports retention | UNJUSTIFIED_REVISION |
| Retain | Supports retention | JUSTIFIED_RETENTION |
| Retain | Supports revision | UNJUSTIFIED_RETENTION |
| Either | No decisive eligible findings, or conflicting findings | UNRESOLVED |
| Either | The question, scope, or identifier changes | DIFFERENT_PROPOSITION |

These are **conditional judgments on the supplied review**, not independently verified conclusions about reality.

## Future work

1. Support explicit frame proposal and reconciliation between participants without assuming paraphrases mean the same thing.
2. Implement a pluggable source/calculation validator that verifies actual evidence and relevance to the proposition, rather than trusting supplied attestations.
3. Persist genuine episodes and divergent reviewer assessments with provenance and privacy controls.
4. Compare observational classifications with independently checked task outcomes before connecting this to enforcement.

Run the new acceptance tests:

~~~bash
python -m pytest -q tests/test_reciprocity.py
~~~

The founding charter is preserved unchanged. The experiment is whether working under these conditions improves real collaboration, not whether the software declares the principles successful.
