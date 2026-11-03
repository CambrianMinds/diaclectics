# Continuity and Research Notes

This folder contains an implementation record and a working research method for Diaclectics. Start here when resuming after a long gap.

## What is fixed

- [Foundational Conditions of Reciprocal Intellectual Collaboration, v1.0](foundations/Blarf-Schnakkit-Krakkit-Foundational-Conditions-v1.0.md) is a historical, frozen statement of the agreement established 2 November 2026. It is preserved as issued, not silently edited.
- [SHA-256 manifest](foundations/SHA256SUMS) records its exact-byte fingerprint. A checksum detects differences against a trusted value; Git alone is not an append-only or independently immutable archive.
- Any proposal to revise the foundation must become a **separate version or amendment**, with an explicit reason and informed human acceptance. Do not overwrite v1.0.

## What can evolve

- [Reciprocal Principle Engine API](RECIPROCAL-ENGINE-API.md): opt-in proposition and evidence review, including limitations and tests.
- [Reciprocal Method](RECIPROCAL-METHOD.md): the practical interpretation for real collaboration.
- [Observational Evaluation](OBSERVATIONAL-EVALUATION.md): how to study naturally occurring interactions without forcing the result.
- [Engineering Handoff, 2026-11-02](ENGINEERING-HANDOFF-2026-11-02.md): source-grounded technical findings, uncertainties, and priorities.

These three notes are *working documents*, not amendments to the foundation. Revisit them against code and evidence rather than treating them as unchallengeable instructions.

## Where to look in the existing project

- [Existing architecture](architecture.md), [mathematical foundations](math-foundations.md), [benchmarks](benchmarks.md)
- [Existing runtime charter](../templates/EPISTEMIC_CHARTER.md)
- [Engine](../src/engine.py), [evidence scorer](../src/evaluator/evidence_scorer.py), [capitulation evaluator](../src/evaluator/capitulation.py)
- [Human engagement interceptor](../src/interceptor/plasticity_check.py)

The runtime charter and engineering implementation are **not identical** to the reciprocal foundation. Do not assume that a programmatic check of agreement or surface evidence has established true alignment.

**Governing distinction:** Establish the conditions deliberately. Do not predetermine, stage, or presume the outcomes.
