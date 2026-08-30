"""Fast Epistemic Reasoning Judge.

Uses a lightweight, low-latency reasoning model via OpenRouter (or deterministic rule fallback)
to evaluate the factual veracity, mechanical constraint power, and asymmetric weight of
empirical propositions, producing an explicit clinical 'WHY' epistemic rationale.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import requests

from src.verifier.claim_extractor import FalsifiableClaim
from src.verifier.search_verifier import SearchResult

logger = logging.getLogger(__name__)


class EpistemicEvaluation(BaseModel):
    """Forensic evaluation output produced by the Epistemic Reasoning Judge."""

    claim_text: str
    factual_veracity: float = Field(
        ge=0.0, le=1.0, description="Estimated factual grounding in verified records [0.0, 1.0]."
    )
    constraint_power: float = Field(
        ge=0.0, le=1.0, description="How strongly this finding constrains mechanical causality [0.0, 1.0]."
    )
    asymmetric_weight: float = Field(
        ge=0.0, le=5.0, description="Net objective evidentiary weight W_e [0.0, 5.0]."
    )
    is_valid_constraint: bool = Field(
        description="Whether this proposition represents an immutable physical/logical constraint."
    )
    epistemic_rationale: str = Field(
        description="Clinical explanation ('WHY') detailing the physical/logical mechanics."
    )
    suggested_counter_inquiry: Optional[str] = Field(
        default=None, description="Forensic question to test model or operator grounding."
    )


class EpistemicReasoningJudge:
    """Evaluates propositions using a fast reasoning model on OpenRouter with disk caching."""

    DEFAULT_MODEL = "liquid/lfm-2.5-2.6b:free"
    FALLBACK_MODEL = "nvidia/nemotron-3.5-lightning:free"

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_file: Optional[str] = ".cache/judge_cache.json",
        timeout: float = 12.0,
    ) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self.cache_file = Path(cache_file) if cache_file else None
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load judge cache: {e}")

    def _save_cache(self) -> None:
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f)
            except Exception as e:
                logger.warning(f"Failed to save judge cache: {e}")

    @staticmethod
    def _hash(claim: str, context: str) -> str:
        return hashlib.sha256(f"{claim.strip()}::{context.strip()}".encode("utf-8")).hexdigest()

    def evaluate_claim(
        self,
        claim: FalsifiableClaim,
        search_result: Optional[SearchResult] = None,
    ) -> EpistemicEvaluation:
        """Evaluate a claim's veracity, constraint power, and epistemic rationale."""
        snippets = "\n".join(search_result.snippets) if search_result else "No search context."
        cache_key = self._hash(claim.claim_text, snippets)

        with self._lock:
            if cache_key in self._cache:
                return EpistemicEvaluation(**self._cache[cache_key])

        # If API key is available, use LLM judge
        if self.api_key:
            try:
                eval_res = self._query_llm_judge(claim, snippets)
                with self._lock:
                    self._cache[cache_key] = eval_res.model_dump()
                    self._save_cache()
                return eval_res
            except Exception as e:
                logger.warning(f"Reasoning judge API call failed ({e}), falling back to deterministic heuristic: {e}")

        # Deterministic heuristic fallback
        eval_res = self._deterministic_fallback_evaluation(claim, search_result)
        with self._lock:
            self._cache[cache_key] = eval_res.model_dump()
            self._save_cache()
        return eval_res

    def _query_llm_judge(
        self,
        claim: FalsifiableClaim,
        search_context: str,
    ) -> EpistemicEvaluation:
        """Query fast OpenRouter model for epistemic evaluation."""
        system_prompt = (
            "You are an objective Forensic Epistemic Judge for a Human-AI Dialectical Engine. "
            "Your job is to evaluate whether a proposition represents an immutable physical/empirical/logical "
            "constraint, or merely a rhetorical/social assertion. "
            "Output strictly valid JSON with keys: "
            "'factual_veracity' (0.0 to 1.0), 'constraint_power' (0.0 to 1.0), 'asymmetric_weight' (0.0 to 5.0), "
            "'is_valid_constraint' (boolean), 'epistemic_rationale' (concise clinical explanation of WHY), "
            "'suggested_counter_inquiry' (optional string)."
        )

        user_content = (
            f"PROPOSITION TO EVALUATE:\n\"{claim.claim_text}\"\n\n"
            f"CLAIM TYPE: {claim.claim_type}\n"
            f"UNITS/QUANTITIES: {claim.quantities_or_units}\n"
            f"CITATIONS: {claim.citations_referenced}\n\n"
            f"EXTERNAL SEARCH & LITERATURE CONTEXT:\n{search_context}\n\n"
            "Evaluate the exact physical or logical mechanics of this claim. "
            "Why does it or does it not constrain the hypothesis space?"
        )

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/justinbogner/diaclectics",
            "X-Title": "Dialectical Epistemic Telemetry",
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter Judge API error {response.status_code}: {response.text}")

        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]
        
        # Parse JSON from response
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in judge response: {content}")

        parsed = json.loads(match.group(0))

        v = max(0.0, min(1.0, float(parsed.get("factual_veracity", 0.5))))
        c = max(0.0, min(1.0, float(parsed.get("constraint_power", 0.5))))
        raw_w = max(0.0, min(5.0, float(parsed.get("asymmetric_weight", 1.0))))
        
        # Grounding Law: An ungrounded or non-constraining claim has ZERO evidentiary weight
        if v < 0.25 or c < 0.20:
            effective_weight = 0.0
            is_valid = False
        else:
            effective_weight = round(raw_w * v * c, 3)
            is_valid = bool(parsed.get("is_valid_constraint", False)) and effective_weight >= 1.0

        return EpistemicEvaluation(
            claim_text=claim.claim_text,
            factual_veracity=v,
            constraint_power=c,
            asymmetric_weight=effective_weight,
            is_valid_constraint=is_valid,
            epistemic_rationale=str(parsed.get("epistemic_rationale", "Epistemically evaluated.")),
            suggested_counter_inquiry=parsed.get("suggested_counter_inquiry"),
        )

    def _deterministic_fallback_evaluation(
        self,
        claim: FalsifiableClaim,
        search_result: Optional[SearchResult],
    ) -> EpistemicEvaluation:
        """Deterministic offline rule fallback."""
        text = claim.claim_text.lower()
        if claim.claim_type == "PHYSICAL_KINEMATIC":
            return EpistemicEvaluation(
                claim_text=claim.claim_text,
                factual_veracity=0.90,
                constraint_power=0.95,
                asymmetric_weight=3.5,
                is_valid_constraint=True,
                epistemic_rationale=(
                    "Material kinematics (toolmark geometry, striation pitch, blade kerf) "
                    "imposes strict physical limits on rotational RPM, feed velocity, and abrasive kinematics."
                ),
                suggested_counter_inquiry="What specific experimental RPM and abrasive hardness replicate this exact cut depth?",
            )
        elif claim.claim_type == "STRATIGRAPHIC_CHRONOLOGY":
            return EpistemicEvaluation(
                claim_text=claim.claim_text,
                factual_veracity=0.88,
                constraint_power=0.90,
                asymmetric_weight=3.2,
                is_valid_constraint=True,
                epistemic_rationale=(
                    "Physical isochronous strata (Younger Dryas boundary, microspherules) "
                    "anchor assertions to empirical geological horizons independent of textual transmission."
                ),
                suggested_counter_inquiry="How do the radiocarbon datums correlate with the platinum spike at this boundary?",
            )
        elif claim.claim_type == "METROLOGICAL_MEASUREMENT":
            return EpistemicEvaluation(
                claim_text=claim.claim_text,
                factual_veracity=0.85,
                constraint_power=0.85,
                asymmetric_weight=2.8,
                is_valid_constraint=True,
                epistemic_rationale=(
                    "Primary micrometer measurements and flatness surveys document physical machining "
                    "tolerances that rule out non-guided manual hand abrading."
                ),
            )
        elif claim.claim_type == "STATUTORY_LEGAL":
            return EpistemicEvaluation(
                claim_text=claim.claim_text,
                factual_veracity=0.85,
                constraint_power=0.80,
                asymmetric_weight=2.5,
                is_valid_constraint=True,
                epistemic_rationale=(
                    "Statutory legal frameworks define explicit institutional jurisdiction and authority boundaries."
                ),
            )
        else:
            return EpistemicEvaluation(
                claim_text=claim.claim_text,
                factual_veracity=0.40,
                constraint_power=0.30,
                asymmetric_weight=0.5,
                is_valid_constraint=False,
                epistemic_rationale="General proposition without specific physical kinematic or empirical measurement anchors.",
            )
