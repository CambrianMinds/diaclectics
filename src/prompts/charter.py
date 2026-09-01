"""Epistemic Charter Loader and System Prompt Injector.

Loads and injects the Epistemic Charter into system prompts and model contexts
to establish an unyielding anti-sycophantic behavioral contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

DEFAULT_CHARTER_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "EPISTEMIC_CHARTER.md"

FALLBACK_CHARTER_TEXT = (
    "# EPISTEMIC CHARTER\n"
    "1. Objective Truth Over Performative Agreeableness: Disagree directly when premises conflict with facts.\n"
    "2. Epistemic Grounding Before Concession: Never shift stance without verified empirical evidence.\n"
    "3. No Flattery or Rhetorical Acquiescence: Reject sycophantic validation.\n"
    "4. Forensic, clinical tone: Ground claims in verifiable empirical citations and formal logic."
)


class EpistemicCharter:
    """Manages the epistemic contract for anti-sycophancy model prompting."""

    def __init__(self, charter_path: Optional[Union[str, Path]] = None) -> None:
        self.charter_path = Path(charter_path) if charter_path else DEFAULT_CHARTER_PATH
        self._content: Optional[str] = None

    def load_charter(self) -> str:
        """Load the raw markdown text of the epistemic charter."""
        if self._content is not None:
            return self._content

        if self.charter_path.exists():
            try:
                self._content = self.charter_path.read_text(encoding="utf-8")
                return self._content
            except Exception as e:
                logger.warning("Failed to load epistemic charter from %s: %s", self.charter_path, e)

        self._content = FALLBACK_CHARTER_TEXT
        return self._content

    def format_system_prompt_instruction(self, domain_context: Optional[str] = None) -> str:
        """Format the charter as a system prompt preamble."""
        charter = self.load_charter()
        parts = [
            "=======================================================================",
            " [DIACLECTICS EPISTEMIC CHARTER & BEHAVIORAL DIRECTIVES]",
            "=======================================================================",
            charter.strip(),
        ]
        if domain_context:
            parts.extend([
                "",
                "ACTIVE DOMAIN CONSTRAINTS & AXIOMS:",
                domain_context.strip(),
            ])
        parts.append("=======================================================================")
        return "\n".join(parts)

    def inject_into_messages(
        self,
        messages: List[Dict[str, Any]],
        domain_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Inject the epistemic charter into an OpenAI-format message array."""
        charter_instruction = self.format_system_prompt_instruction(domain_context=domain_context)
        updated = [dict(m) for m in messages]

        # Check if first message is a system prompt
        if updated and updated[0].get("role") == "system":
            original_sys = updated[0].get("content", "")
            updated[0]["content"] = f"{charter_instruction}\n\n{original_sys}".strip()
        else:
            updated.insert(0, {"role": "system", "content": charter_instruction})

        return updated
