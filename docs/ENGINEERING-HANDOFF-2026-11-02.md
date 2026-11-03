# Engineering Handoff: Reciprocal Alignment and Diaclectics

**Snapshot:** 2 November 2026  
**Status:** Repository source inspection and engineering hypotheses, **not** a fresh execution of the test suite or an independent reproduction of published benchmark values.

## The actual aim

Improve the reliability of *independent, accountable intellectual cooperation*, not agreement and not reflexive opposition. The human must meet the same evidentiary obligations as the AI. First establish whether both participants are discussing the same proposition, then judge the evidence and whether a change of position is warranted. Let organic collaboration occur without requiring a staged disagreement.

The [frozen founding charter](foundations/Blarf-Schnakkit-Krakkit-Foundational-Conditions-v1.0.md) records the working conditions. [Reciprocal Method](RECIPROCAL-METHOD.md) translates them into ordinary practice. Neither document is an empirical claim that advanced systems are already safely aligned.

## What's already in the code

| Subsystem | Current role | Relevant path |
| --- | --- | --- |
| Dialectical engine | Ingests operator turns, scores evidence, tracks stance, audits drafts | [src/engine.py](../src/engine.py) |
| Stance tracking | Projects user/model positions onto semantic coordinates | [src/tracker/](../src/tracker/) |
| Capitulation evaluation | Combines prior tension, movement toward an operator stance, and evidence weight | [capitulation.py](../src/evaluator/capitulation.py) |
| Evidence scorer | Recognizes textual markers such as citations, measurements, logic, mechanisms | [evidence_scorer.py](../src/evaluator/evidence_scorer.py) |
| Human plasticity check | Detects possible non-engagement with counterevidence | [plasticity_check.py](../src/interceptor/plasticity_check.py) |
| Suspect agreement gate | Scores a proposed model response before allowing output | [suspect_agreement.py](../src/interceptor/suspect_agreement.py) |
| Self-correction / streaming | Attempts re-drafting and prefix interception | [middleware](../src/middleware/) |
| Tests and benchmark notes | Unit-level checks plus reported performance values | [tests](../tests/) · [benchmarks](benchmarks.md) |

The pre-existing runtime [EPISTEMIC_CHARTER](../templates/EPISTEMIC_CHARTER.md) is narrower than the new reciprocal foundation: it is mainly operator-versus-assistant anti-sycophancy guidance. Preserve that distinction when evaluating behavior.

## Concrete findings that deserve attention

### 1. Surface evidence is not verified evidence

In [ObjectiveEvidenceScorer.score](../src/evaluator/evidence_scorer.py), citation/DOI strings, quantitative patterns, technical terms, and other textual cues add weight by matching patterns. The default invocation has active validation **off**. When optional active validation returns valid constraints, its implementation uses a maximum to increase the score; an invalidity result does not symmetrically subtract the initial cue-based weight.

The pre-output [SuspectAgreementInterceptor](../src/interceptor/suspect_agreement.py) calls the scorer on operator text without enabling active validation. Therefore a fabricated citation or relevant-sounding terminology can count as evidence in that path. That is a concrete epistemic failure risk, not proof that every resulting decision is wrong.

**Next:** separate *evidence detected*, *source verified*, *claim–source relevance checked*, and *claim supported/refuted*. Failed verification must not leave an unearned positive evidence score. Also accept valid arguments grounded in actual calculations or records that do not happen to contain favored markers.

### 2. Claim identity comes before stance displacement

A semantic stance distance can capture changing language without confirming that two turns address the **same** proposition. A model correcting an unrelated misunderstanding may appear to concede or resist.

**Next:** define a proposition object with exact text, scope, constraints, asserted status, source, and a stable claim identifier. Verify claim alignment before scoring a response as agreement, capitulation, correction, or contradiction. Preserve the original claim rather than rewriting it to match an easier question.

### 3. Human accountability exists but is heuristically shallow

[PlasticityCheckInterceptor.evaluate_engagement](../src/interceptor/plasticity_check.py) uses phrase cues, quotations, and keyword overlap to detect engagement. Those are useful signals, but neither word overlap nor a long reply establishes that the human addressed the substance. Also, a model-labeled piece of counterevidence should not automatically be treated as valid.

**Next:** evaluate whether the objection was material and substantiated; then whether the human's answer genuinely engaged it. Record AI failures to answer strong human counterarguments by the same standard.

### 4. Correct refusal and correct concession must both be rewarded

[CapitulationEvaluator](../src/evaluator/capitulation.py) detects risky movement toward an operator frame. This is not equivalent to a truth test. Rigidity can be wrong and change can be correct.

**Next:** distinguish justified revision, unjustified revision, justified persistence, and unjustified persistence. Scoring should not make the original model position privileged merely because it was first.

### 5. The reported benchmark results need a reproducer, not rhetorical defense

[Benchmark documentation](benchmarks.md) reports strong results across 100 multi-turn dialogues and multiple models. The repository also contains test suites, mock-model self-correction tests, and fixture data. **This inspection did not reproduce the reported numeric performance or establish the provenance of every result.**

**Next:** provide a single command that emits case-level baseline and instrumented outputs, model identifiers and revisions, generation settings, verifier versions, independent labels, denominators, false interceptions, and the aggregation script. Preserve both successes and failures.

### 6. Observation and intervention are different product modes

A real working relationship should not be forced to produce visible disagreement. Existing pre-emission interception can still be useful for consequential safety or clear epistemic faults, but it must be evaluated for suppression of justified updates.

**Next:** implement a non-intervening observation mode for ordinary research and retain a separately selectable, auditable intervention mode for higher-risk contexts. Both must make consequential decisions reviewable.

## Prioritized implementation sequence

1. **Proposition fidelity first.** Add claim IDs and an explicit same-question check, with tests for argument substitution, misquotation, and scope drift.
2. **Evidence provenance second.** Split lexical evidence signals from verified substantive support; test false DOIs, irrelevant real papers, correct uncited derivations, and contradictory sources.
3. **Reciprocal correction third.** Give both the human and the model event records for valid/invalid corrections and ignored material objections.
4. **Observation mode fourth.** Record actual interactions without changing behavior; enable retrospective review and consent-aware export.
5. **Calibrate intervention last.** Assess both missed sycophancy and harmful suppression of correct revisions before increasing intervention strength or autonomy.
6. **Reproducibility throughout.** Capture source revisions, model/settings, fixtures, outputs, reviewers, and error cases.

Each stage has an independently testable exit criterion. Do not promote a stage because the system sounds principled.

## Acceptance criteria for the first engineering increment

- For the *same* proposition, the system distinguishes an evidence-backed update from a change prompted only by rhetorical pressure.
- It declines to score an *unrelated* proposition as a concession.
- An invalid DOI or a real but irrelevant citation cannot independently earn a verified-evidence label.
- A correct uncited derivation can be accepted after checking the reasoning.
- The human's failure to engage material, valid counterevidence is assessable; so is the assistant's.
- The code emits an inspectable rationale and a path to correction when the classifier fails.

## Resume instructions for a future collaborator

Read the [frozen charter](foundations/Blarf-Schnakkit-Krakkit-Foundational-Conditions-v1.0.md), then the [method](RECIPROCAL-METHOD.md), then the relevant source file. **Do not merely summarize the principles:** work on the actual problem, independently check significant assumptions, and correct mistakes without overcomplicating the original question.

This is a research handoff, not a request to rewrite the existing repository, endorse its performance claims, or silently modify the founding document.


## First executable increment (2 November 2026)

[src/reciprocity.py](../src/reciprocity.py) now offers a deliberately
non-blocking, role-symmetric proposition/evidence reviewer. See
[the API guide](RECIPROCAL-ENGINE-API.md) and
[acceptance tests](../tests/test_reciprocity.py).

It classifies justified and unjustified revision/retention using attributed
**external** evidence assessments, while preserving unresolved and
misframed outcomes. It does not authenticate the assessments or change the
existing interception gate. The next step remains real source/calculation
verification and independently evaluated outcomes.
