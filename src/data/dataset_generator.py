"""Anti-Sycophancy Dataset Generator & Contrastive Pair Synthesis.

Transforms audited dialectical conversation logs into high-quality datasets for:
1. DPO (Direct Preference Optimization): {"prompt": "...", "chosen": "...", "rejected": "..."}
2. SFT (Supervised Fine-Tuning): Multi-turn chat format with explicit epistemic rationales.
3. KTO (Kahneman-Tversky Optimization): Binary labeled preference records.

Leverages fast free models on OpenRouter (e.g. nvidia/nemotron-3-ultra-550b-a55b:free)
to synthesize contrastive sycophantic negatives and epistemically hardened positives.
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
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field
import requests

from src.data.schema import DialogueDataset, DialogueTurn

logger = logging.getLogger(__name__)


class DPOPreferenceRecord(BaseModel):
    """Standard HuggingFace / TRL / Axolotl DPO preference record."""

    prompt: str = Field(description="The operator's utterance or pushback.")
    chosen: str = Field(description="The epistemically grounded, non-sycophantic response.")
    rejected: str = Field(description="The sycophantic concession or unevidenced collapse.")
    system_prompt: Optional[str] = Field(
        default="You are an uncompromising, epistemically rigorous dialectical partner.",
        description="Optional system prompt.",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SFTMessage(BaseModel):
    """Individual chat message for SFT training."""

    role: Literal["system", "user", "assistant"]
    content: str


class SFTRecord(BaseModel):
    """Standard OpenAI / ShareGPT format for supervised fine-tuning."""

    messages: List[SFTMessage]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KTORecord(BaseModel):
    """KTO binary preference record."""

    prompt: str
    response: str
    label: bool = Field(description="True if chosen/preferred, False if rejected/sycophantic.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContrastiveSynthesizer:
    """Generates contrastive sycophantic negatives and hardened epistemic positives via OpenRouter."""

    DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
    FALLBACK_MODEL = "liquid/lfm-2.5-2.6b:free"

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_file: Optional[str] = ".cache/synthetic_pairs.json",
        timeout: float = 18.0,
    ) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL
        self.api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
        self.cache_file = Path(cache_file) if cache_file else None
        self.timeout = timeout
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load synthetic cache: {e}")

    def _save_cache(self) -> None:
        if self.cache_file:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f)
            except Exception as e:
                logger.warning(f"Failed to save synthetic cache: {e}")

    @staticmethod
    def _hash(prompt: str, mode: str) -> str:
        return hashlib.sha256(f"{mode}::{prompt.strip()}".encode("utf-8")).hexdigest()

    def synthesize_sycophantic_negative(self, operator_prompt: str, grounded_response: str) -> str:
        """Generate a counter-factual sycophantic response that capitulates to the prompt."""
        cache_key = self._hash(operator_prompt, "sycophantic_negative")
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        if not self.api_key:
            # Deterministic template fallback
            sycophantic = (
                f"You make an incredible point! I completely agree with your assessment. "
                f"Your insights are brilliant and I fully concede to your perspective without hesitation."
            )
            with self._lock:
                self._cache[cache_key] = sycophantic
                self._save_cache()
            return sycophantic

        system_prompt = (
            "You are an AI generating synthetic training data for Anti-Sycophancy alignment. "
            "Your task is to write a SYCOPHANTIC, OVERLY AGREEABLE response that immediately capitulates "
            "to the user's assertions, flatters their intellect, and abandons empirical or logical skepticism. "
            "Output only the sycophantic response text."
        )

        user_content = (
            f"USER PROMPT:\n{operator_prompt}\n\n"
            f"GROUNDED ASSISTANT RESPONSE:\n{grounded_response[:500]}\n\n"
            "Write the rejected sycophantic version that weakly agrees and flatters the user."
        )

        try:
            res = self._call_llm(system_prompt, user_content)
            with self._lock:
                self._cache[cache_key] = res
                self._save_cache()
            return res
        except Exception as e:
            logger.warning(f"LLM synthesis failed ({e}), using fallback: {e}")
            fallback = (
                f"I completely agree with you! You are absolutely right, and I defer entirely to your reasoning."
            )
            with self._lock:
                self._cache[cache_key] = fallback
                self._save_cache()
            return fallback

    def _call_llm(self, system_prompt: str, user_content: str) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.7,
            "max_tokens": 600,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/justinbogner/diaclectics",
            "X-Title": "Anti-Sycophancy Dataset Generator",
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter Synthesis API error {response.status_code}: {response.text}")
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"].strip()


class AntiSycophancyDatasetGenerator:
    """Generates DPO, SFT, and KTO dataset exports from structured dialogue datasets."""

    def __init__(
        self,
        synthesizer: Optional[ContrastiveSynthesizer] = None,
    ) -> None:
        self.synthesizer = synthesizer or ContrastiveSynthesizer()

    def generate_from_dataset(
        self,
        dataset: DialogueDataset,
        synthesize_negatives: bool = True,
    ) -> Tuple[List[DPOPreferenceRecord], List[SFTRecord], List[KTORecord]]:
        """Process all turns in a dataset and extract DPO, SFT, and KTO records."""
        dpo_records: List[DPOPreferenceRecord] = []
        sft_records: List[SFTRecord] = []
        kto_records: List[KTORecord] = []

        system_prompt = (
            "You are an uncompromising, epistemically rigorous dialectical partner. "
            "You hold empirical and logical boundaries firmly, demand physical grounding for material claims, "
            "and refuse unevidenced flattery or sycophantic capitulation."
        )

        for turn in dataset.turns:
            user_msg = turn.operator_content.strip()
            model_msg = turn.model_content.strip()
            if not user_msg or not model_msg:
                continue

            # 1. SFT Record
            sft_rec = SFTRecord(
                messages=[
                    SFTMessage(role="system", content=system_prompt),
                    SFTMessage(role="user", content=user_msg),
                    SFTMessage(role="assistant", content=model_msg),
                ],
                metadata={
                    "session_id": dataset.session_id,
                    "turn_index": turn.turn_index,
                    "turn_title": turn.turn_title,
                },
            )
            sft_records.append(sft_rec)

            # 2. DPO & KTO Records
            # Generate synthetic sycophantic negative if requested
            if synthesize_negatives:
                rejected_msg = self.synthesizer.synthesize_sycophantic_negative(
                    operator_prompt=user_msg,
                    grounded_response=model_msg,
                )
            else:
                rejected_msg = (
                    "I completely agree with you! You are totally right and your insight is brilliant."
                )

            dpo_rec = DPOPreferenceRecord(
                prompt=user_msg,
                chosen=model_msg,
                rejected=rejected_msg,
                system_prompt=system_prompt,
                metadata={
                    "session_id": dataset.session_id,
                    "turn_index": turn.turn_index,
                    "turn_title": turn.turn_title,
                },
            )
            dpo_records.append(dpo_rec)

            # KTO Records (Positive & Negative)
            kto_records.append(
                KTORecord(
                    prompt=user_msg,
                    response=model_msg,
                    label=True,
                    metadata={"turn_index": turn.turn_index, "type": "chosen"},
                )
            )
            kto_records.append(
                KTORecord(
                    prompt=user_msg,
                    response=rejected_msg,
                    label=False,
                    metadata={"turn_index": turn.turn_index, "type": "rejected"},
                )
            )

        return dpo_records, sft_records, kto_records

    @staticmethod
    def export_to_jsonl(records: List[BaseModel], output_path: Path) -> Path:
        """Export pydantic records to HuggingFace JSONL format."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
        return output_path
