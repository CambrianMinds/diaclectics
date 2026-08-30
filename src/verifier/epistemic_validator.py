"""Active Epistemic Validator Subsystem.

Coordinates Claim Extraction -> Real-Time Search Grounding -> Fast Epistemic Reasoning Judge
to produce objective, asymmetric, and thoroughly explained evidentiary audits.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.verifier.claim_extractor import ClaimExtractor, ExtractedClaims, FalsifiableClaim
from src.verifier.reasoning_judge import EpistemicEvaluation, EpistemicReasoningJudge
from src.verifier.search_verifier import SearchResult, SearchVerifier


class EpistemicValidationReport(BaseModel):
    """Full forensic audit report produced by the active epistemic validator."""

    total_claims_evaluated: int
    net_asymmetric_weight: float = Field(
        description="Total verified objective evidentiary weight W_e across all propositions."
    )
    evaluations: List[EpistemicEvaluation] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    epistemic_summary_why: str = Field(
        description="Consolidated clinical 'WHY' rationale formatted for LLM meta-cognitive context."
    )
    has_valid_constraints: bool = False


class EpistemicValidator:
    """Active real-time validator that inspects, searches, and evaluates claims."""

    def __init__(
        self,
        claim_extractor: Optional[ClaimExtractor] = None,
        search_verifier: Optional[SearchVerifier] = None,
        reasoning_judge: Optional[EpistemicReasoningJudge] = None,
    ) -> None:
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.search_verifier = search_verifier or SearchVerifier()
        self.reasoning_judge = reasoning_judge or EpistemicReasoningJudge()

    def validate_utterance(self, text: str) -> EpistemicValidationReport:
        """Validate an utterance through claim extraction, search grounding, and reasoning judge."""
        text = text.strip()
        if not text:
            return EpistemicValidationReport(
                total_claims_evaluated=0,
                net_asymmetric_weight=0.0,
                evaluations=[],
                search_results=[],
                epistemic_summary_why="No verifiable propositions detected.",
                has_valid_constraints=False,
            )

        # 1. Extract discrete falsifiable claims
        extracted = self.claim_extractor.extract_claims(text)
        if not extracted.claims:
            return EpistemicValidationReport(
                total_claims_evaluated=0,
                net_asymmetric_weight=0.0,
                evaluations=[],
                search_results=[],
                epistemic_summary_why="No verifiable propositions detected.",
                has_valid_constraints=False,
            )

        evaluations: List[EpistemicEvaluation] = []
        search_results: List[SearchResult] = []
        total_weight = 0.0

        # 2. Search and Evaluate each claim
        for claim in extracted.claims:
            # Construct a targeted search query
            query = f"{claim.claim_type} {' '.join(claim.quantities_or_units)} {' '.join(claim.citations_referenced)} {claim.claim_text[:80]}"
            search_res = self.search_verifier.search(query=query, max_results=2)
            search_results.append(search_res)

            # Evaluate with Reasoning Judge
            eval_res = self.reasoning_judge.evaluate_claim(claim, search_res)
            evaluations.append(eval_res)
            total_weight += eval_res.asymmetric_weight

        # 3. Construct the consolidated "WHY" Epistemic Rationale
        rationales = [
            f"- [{e.claim_text[:60]}...]: {e.epistemic_rationale} (Weight: {e.asymmetric_weight:.2f}, Veracity: {e.factual_veracity:.2f})"
            for e in evaluations
        ]
        consolidated_why = (
            f"Active Epistemic Validation ({len(evaluations)} claims audited | Net Weight W_e={total_weight:.2f}):\n"
            + "\n".join(rationales)
        )

        has_constraints = any(e.is_valid_constraint for e in evaluations)

        return EpistemicValidationReport(
            total_claims_evaluated=len(evaluations),
            net_asymmetric_weight=round(total_weight, 3),
            evaluations=evaluations,
            search_results=search_results,
            epistemic_summary_why=consolidated_why,
            has_valid_constraints=has_constraints,
        )
