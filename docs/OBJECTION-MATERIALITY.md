# Objection Materiality: An Operational Filter

**Status:** Working collaboration protocol, 2 November 2026. Not an amendment to the [frozen foundational charter](foundations/Blarf-Schnakkit-Krakkit-Foundational-Conditions-v1.0.md).  
**Applies to:** Both human and AI collaborators when evaluating arguments, code reviews, research, drafts, and each other's criticisms.  
**Related:** [Reciprocal Method](RECIPROCAL-METHOD.md) · [Observational Evaluation](OBSERVATIONAL-EVALUATION.md)

## The failure this addresses

While reviewing another AI's technically useful assessment of Diaclectics, the assistant challenged its statement that the project was "one of the few" efforts addressing reciprocal epistemic integrity. The assistant demanded comparative literature validation. The statement was contextual rhetoric, not a premise supporting the engineering diagnosis. Whether that description was true had no bearing on the identified defect, its tests, or the proposed repair.

**Failure mode:** treating every factual-sounding sentence as a claim requiring immediate verification, irrespective of its *function in the argument* or its *consequence for the work*.

The criticism was not necessarily false. It was **irrelevant to the task at hand**. It diverted attention from substantive engineering findings and made critical scrutiny into a performance.

## Decision procedure: before raising an objection

Use these four checks as a silent, lightweight checkpoint, not as an obligatory script in every reply:

1. **Proposition fidelity.** What is the actual question, claim, or decision under examination? Have both participants established the same referent and scope? Ambiguity can originate with either participant.
2. **Argumentative function.** Is the suspect statement a factual *premise*, necessary inference, result, hypothesis, rhetorical emphasis, incidental description, or separate assertion? Its grammatical form alone does not establish its evidentiary role.
3. **Counterfactual materiality.** If the statement is mistaken, *what changes* about the central argument, measurements, reproducibility, feasibility, safety, interpretation, or next decision? Specify the possible consequence rather than saying merely that the statement is "unverified."
4. **Useful intervention.** Can I actually improve the work by checking, calculating, correcting, or asking for the missing distinction? If so, address the consequential point in proportion to its stakes. If not, do not turn the incidental issue into a substantive criticism.

**Default rule:** A criticism without an identifiable material consequence does not belong in a substantive evaluation.

A *plausible, specific* consequence suffices to trigger further examination when the stakes warrant it, particularly for safety, decisions with downstream effects, or a claim that may seriously mislead. Materiality is not an excuse to conceal important inaccuracies.

## Do not confuse these distinctions

- **True/false is not the same as relevant/irrelevant.** A false rhetorical flourish may be immaterial to an engineering review. A true statement can be entirely beside the point.
- **Rhetoric is not automatically evidence.** Do not convert contextual characterization into a required premise of the work.
- **Rhetorical wording is not automatically exempt.** When the task *is* assessing originality, novelty, literature coverage, or public-facing factual accuracy, "one of the few" *is* a material claim and may need research.
- **Material doesn't mean hostile.** A justified objection may improve a favored proposal; an unsupported objection must be withdrawn.
- **Scope correction isn't obstruction.** Establishing that interlocutors mean different things is useful when the difference affects the conclusion.
- **No objection required.** Intellectual independence does not require inventing a criticism to make an assessment appear balanced.
- **No symmetry exception.** Apply the same materiality test to remarks made by the human, the assistant, or another AI.

## Worked cases

| Actual task | Candidate issue | Material? | Proper response |
| --- | --- | --- | --- |
| Evaluate a specific software defect and repair | Reviewer calls the project "one of the few" of its kind | **No**, unless novelty is at issue | Evaluate the defect. Do not demand a literature survey to validate an incidental compliment. |
| Establish whether the project is novel | Reviewer calls the project "one of the few" of its kind | **Yes** | Define the comparison class and check relevant prior research. |
| Assess a claimed evidence-backed correction | DOI-shaped citation does not support the asserted proposition | **Yes** | Verify source existence, relevance, and claim support; don't count citation syntax as proof. |
| Evaluate whether a proposed fabrication process can work | Spindle clearance conflicts with proposed tool geometry | **Yes** | Compute the complete motion/clearance envelope; the objection changes physical feasibility. |
| Evaluate whether a rebuttal answers a claim | Rebuttal substitutes a different proposition | **Yes** | Restore the original proposition before assigning a verdict. |
| Evaluate a proposed implementation | An incidental stylistic flourish changes no functionality or claim | **No** | Ignore it in the engineering assessment; optionally suggest a copy edit only when asked. |
| Assess benchmark results | Claimed false-interception rate lacks traceable run data | **Yes** | Request case-level provenance; it changes how confidently performance can be stated. |
| Review an actual safety-critical action | A suspicious detail may signal a consequential hazard | **Potentially yes** | Investigate the specific hazard even if it was not a premise in the main argument. |

## Operational use in Diaclectics

Apply this filter **before** any attempt to classify a human or model's statement as a substantive objection, error, correction, capitulation, or refusal. Do not use a heuristic to automatically suppress all issues labeled "rhetorical"; argument role and consequences depend on context.

A minimal record for substantive reviews:

- **Target:** the original proposition and task.
- **Role:** what function the contested statement plays in that task.
- **Counterfactual:** what would change if it were wrong.
- **Action:** check/calculate/correct now; note separately for editorial review; or omit from the substantive critique.
- **Outcome:** did the intervention actually improve accuracy, understanding, safety, or the work product?

If another participant challenges an objection's relevance, revisit the *counterfactual* before defending the objection's literal truth.

This is currently a **working procedural requirement**, not a software-enforced guarantee. The [reciprocity module](../src/reciprocity.py) does not implement semantic argument-role or materiality classification. For future evaluations, use the [materiality cases](../data/evals/materiality_cases.jsonl) as illustrative reviewer labels, not as validated model performance.

## How to assess improvement

In naturally occurring work, watch for:
- **False-positive criticism:** immaterial objections surfaced as substantive flaws.
- **False-negative criticism:** consequential defects missed while focusing on tone or niceties.
- **Argument substitution:** assessment of an easier or different proposition.
- **Repair effectiveness:** whether a correction reduced repeated supervision and led to a useful next result.

The goal is not zero criticism. It is **criticism concentrated where the consequences actually are**. A correction is demonstrated by changed decisions on subsequent work, not by repeating this document's language.

**Practical rule:** Before objecting, identify what the objection changes. If it changes nothing important to the task, return to the task.
